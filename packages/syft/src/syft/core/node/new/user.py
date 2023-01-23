# stdlib
from enum import Enum
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type

# third party
from bcrypt import gensalt
from bcrypt import hashpw
from result import Err
from result import Ok
from result import Result

# relative
from ....core.node.common.node_table.syft_object import SyftObject
from ....core.node.common.node_table.syft_object import transform
from ...common.serde.serializable import serializable
from ...common.uid import UID
from .credentials import SyftSigningKey
from .credentials import SyftVerifyKey
from .service import AbstractNode
from .service import AbstractService
from .service import service_method
from .transforms import drop
from .transforms import keep
from .transforms import make_set_default


class ServiceRoleCapability(Enum):
    CAN_MAKE_DATA_REQUESTS = 1
    CAN_TRIAGE_DATA_REQUESTS = 2
    CAN_MANAGE_PRIVACY_BUDGET = 4
    CAN_CREATE_USERS = 8
    CAN_MANAGE_USERS = 16
    CAN_EDIT_ROLES = 32
    CAN_MANAGE_INFRASTRUCTURE = 64
    CAN_UPLOAD_DATA = 128
    CAN_UPLOAD_LEGAL_DOCUMENT = 256
    CAN_EDIT_DOMAIN_SETTINGS = 512


@serializable(recursive_serde=True)
class ServiceRole(Enum):
    GUEST = 1


@serializable(recursive_serde=True)
class User(SyftObject):
    # version
    __canonical_name__ = "User"
    __version__ = 1

    # fields
    email: str
    name: str
    hashed_password: str
    salt: str
    signing_key: SyftSigningKey
    verify_key: SyftVerifyKey
    role: ServiceRole
    created_at: Optional[str]

    # serde / storage rules
    __attr_state__ = [
        "email",
        "name",
        "hashed_password",
        "salt",
        "signing_key",
        "verify_key",
        "role",
        "created_at",
    ]
    __attr_searchable__ = ["name", "email", "verify_key"]
    __attr_unique__ = ["email", "signing_key"]


def default_role(role: ServiceRole) -> Callable:
    return make_set_default(key="role", value=role)


def hash_password(output: dict):
    if output["password"] == output["password_verify"]:
        salt, hashed = __salt_and_hash_password(output["password"], 12)
        output["hashed_password"] = hashed
        output["salt"] = salt
    return output


def generate_key(output: dict) -> dict:
    signing_key = SyftSigningKey.generate()
    output["signing_key"] = signing_key
    output["verify_key"] = signing_key.verify_key
    return output


def __salt_and_hash_password(password: str, rounds: int) -> Tuple[str, str]:
    bytes_pass = password.encode("UTF-8")
    salt = gensalt(rounds=rounds)
    salt_len = len(salt)
    hashed = hashpw(bytes_pass, salt)
    hashed = hashed[:salt_len]
    hashed = hashed.decode("UTF-8")
    salt = salt.decode("UTF-8")
    return salt, hashed


def check_pwd(password: str, salt: str, hashed_password: str) -> bool:
    bytes_pwd = password.encode("utf-8")
    bytes_salt = salt.encode("utf-8")
    salt_len = len(salt)

    gen_pwd_hash = hashpw(bytes_pwd, bytes_salt)[:salt_len]
    return gen_pwd_hash.decode("utf-8") == hashed_password


@serializable(recursive_serde=True)
class UserUpdate(SyftObject):
    __canonical_name__ = "UserUpdate"
    __version__ = 1

    email: str
    name: str
    role: Optional[ServiceRole] = None  # make sure role cant be set without uid
    password: Optional[str] = None
    password_verify: Optional[str] = None
    verify_key: Optional[SyftVerifyKey] = None


@transform(UserUpdate, User)
def user_update_to_user() -> List[Callable]:
    return [
        hash_password,
        generate_key,
        default_role(ServiceRole.GUEST),
        drop(["password", "password_verify"]),
    ]


@transform(User, UserUpdate)
def user_to_update_user() -> List[Callable]:
    return [keep(["id", "email", "name", "role", "verify_key"])]


@serializable(recursive_serde=True)
class UserVerify(SyftObject):
    __canonical_name__ = "UserVerify"
    __version__ = 1

    email: str
    password: Optional[str] = None
    verify_key: Optional[SyftVerifyKey] = None


@transform(User, UserVerify)
def user_to_user_verify() -> List[Callable]:
    return [keep(["email", "verify_key"])]


class SyftServiceRegistry:
    __service_registry__: Dict[str, Callable] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "__canonical_name__") and hasattr(cls, "__version__"):
            mapping_string = f"{cls.__canonical_name__}_{cls.__version__}"
            cls.__object_version_registry__[mapping_string] = cls

    @classmethod
    def versioned_class(cls, name: str, version: int) -> Optional[Type["SyftObject"]]:
        mapping_string = f"{name}_{version}"
        if mapping_string not in cls.__object_version_registry__:
            return None
        return cls.__object_version_registry__[mapping_string]

    @classmethod
    def add_transform(
        cls,
        klass_from: str,
        version_from: int,
        klass_to: str,
        version_to: int,
        method: Callable,
    ) -> None:
        mapping_string = f"{klass_from}_{version_from}_x_{klass_to}_{version_to}"
        cls.__object_transform_registry__[mapping_string] = method

    @classmethod
    def get_transform(
        cls, type_from: Type["SyftObject"], type_to: Type["SyftObject"]
    ) -> Callable:
        klass_from = type_from.__canonical_name__
        version_from = type_from.__version__
        klass_to = type_to.__canonical_name__
        version_to = type_to.__version__
        mapping_string = f"{klass_from}_{version_from}_x_{klass_to}_{version_to}"
        return cls.__object_transform_registry__[mapping_string]


class UserCollection(AbstractService):
    def __init__(self, node: AbstractNode) -> None:
        self.node = node
        self.node_uid = node.id
        self.data = {}
        self.primary_keys = {}

    # @service(path="services.happy.maybe_create", name="create_user")
    @service_method(path="user.create", name="create")
    def create(
        self, credentials: SyftVerifyKey, user_update: UserUpdate
    ) -> Result[UserUpdate, str]:
        """TEST MY DOCS"""
        if user_update.id is None:
            user_update.id = UID()
        user = user_update.to(User)

        result = self.set(credentials=credentials, uid=user.id, syft_object=user)
        if result.is_ok():
            return Ok(user.to(UserUpdate))
        else:
            return Err("Failed to create User.")

    @service_method(path="user.view", name="view")
    def view(self, credentials: SyftVerifyKey, uid: UID) -> Result[UserUpdate, str]:
        user_result = self.get(credentials=credentials, uid=uid)
        if user_result.is_ok():
            return Ok(user_result.ok().to(UserUpdate))
        else:
            return Err(f"Failed to get User for UID: {uid}")

    def set(
        self, credentials: SyftVerifyKey, uid: UID, syft_object: SyftObject
    ) -> Result[bool, str]:
        self.data[uid] = syft_object.to_mongo()
        return Ok(True)

    def verify(
        self, credentials: SyftVerifyKey, searched_user: UserVerify
    ) -> Result[UserUpdate, str]:
        """Verify user
        TODO: We might want to use a SyftObject instead
        """
        user_found = None
        for _, user in self.data.items():
            syft_object: User = SyftObject.from_mongo(user)
            if (syft_object.email == searched_user.email) and check_pwd(
                searched_user.password, syft_object.salt, syft_object.hashed_password
            ):
                user_found = syft_object
                break

        if searched_user is not None:
            return Ok(user_found.to(UserVerify))

        return Err(
            f"No user exists with {searched_user.email} and {searched_user.password}."
        )

    def get(self, credentials: SyftVerifyKey, uid: UID) -> Result[SyftObject, str]:
        print("self.data", self.data.keys())
        if uid not in self.data:
            return Err(f"UID: {uid} not in {type(self)} store.")
        syft_object = SyftObject.from_mongo(self.data[uid])
        return Ok(syft_object)
