# stdlib

# third party

# syft absolute
from syft.core.node.new.client import SyftClient
from syft.core.node.new.context import AuthedServiceContext
from syft.core.node.new.credentials import SyftVerifyKey
from syft.core.node.new.request import Request
from syft.core.node.new.request import SubmitRequest
from syft.core.node.new.request_stash import RequestStash


def test_requeststash_get_all_for_verify_key_no_requests(
    request_stash: RequestStash,
    guest_domain_client: SyftClient,
) -> None:
    # test when there are no requests from a client

    verify_key: SyftVerifyKey = guest_domain_client.credentials.verify_key
    requests = request_stash.get_all_for_verify_key(verify_key=verify_key)
    assert requests.is_ok() is True
    assert len(requests.ok()) == 0


def test_requeststash_get_all_for_verify_key_success(
    request_stash: RequestStash,
    guest_domain_client: SyftClient,
    authed_context_guest_domain_client: AuthedServiceContext,
) -> None:
    # test when there is one request
    submit_request: SubmitRequest = SubmitRequest(changes=[])
    stash_set_result = request_stash.set(
        submit_request.to(Request, context=authed_context_guest_domain_client)
    )

    verify_key: SyftVerifyKey = guest_domain_client.credentials.verify_key
    requests = request_stash.get_all_for_verify_key(verify_key)

    assert requests.is_ok() is True
    assert len(requests.ok()) == 1
    assert requests.ok()[0] == stash_set_result.ok()

    # add another request
    submit_request_2: SubmitRequest = SubmitRequest(changes=[])
    stash_set_result_2 = request_stash.set(
        submit_request_2.to(Request, context=authed_context_guest_domain_client)
    )
    requests = request_stash.get_all_for_verify_key(verify_key)

    assert requests.is_ok() is True
    assert len(requests.ok()) == 2
    # the order might change so we check all requests
    assert (
        requests.ok()[1] == stash_set_result_2.ok()
        or requests.ok()[0] == stash_set_result_2.ok()
    )


# def test_requeststash_get_all_for_verify_key_error(
#     request_stash: RequestStash,
#     monkeypatch: MonkeyPatch,
# ) -> None:
#     qk = "Query Key"
#     Err(
#         f"{qk} not in {type(request_stash.store.partition)} unique or searchable keys"
#     )

# def mock_stash_get_all_error() -> Err:
#     return Err(mock_error_message)

# monkeypatch.setattr(request_stash.stash, "get_all", mock_stash_get_all_error)

# assert False

#  def test_requeststash_get_all_for_status


#  def test_requeststash_get_all_for_status_error
