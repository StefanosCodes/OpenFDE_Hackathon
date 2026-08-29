import pytest

from app.integrations.github.security import InvalidState, StateSigner, new_pkce_pair


def test_signed_state_round_trip_and_purpose_isolation():
    signer = StateSigner("a-secure-state-secret-with-enough-length")
    state = signer.sign(purpose="github_install", claims={"user_id": "user-1"})

    assert signer.verify(state, purpose="github_install")["user_id"] == "user-1"
    with pytest.raises(InvalidState, match="purpose"):
        signer.verify(state, purpose="github_oauth")


def test_tampered_state_is_rejected():
    signer = StateSigner("a-secure-state-secret-with-enough-length")
    state = signer.sign(purpose="github_install", claims={"user_id": "user-1"})
    encoded, signature = state.split(".", 1)

    with pytest.raises(InvalidState, match="signature"):
        signer.verify(f"{encoded}x.{signature}", purpose="github_install")


def test_pkce_values_are_unique_and_url_safe():
    verifier_a, challenge_a = new_pkce_pair()
    verifier_b, challenge_b = new_pkce_pair()

    assert verifier_a != verifier_b
    assert challenge_a != challenge_b
    assert "=" not in challenge_a
