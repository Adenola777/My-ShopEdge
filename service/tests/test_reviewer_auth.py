"""The reviewer credential path in auth.py, added 7 October 2026 for the TikTok review.

It runs without a database, a network or the provider. It generates its own ES256 key,
configures it as REVIEWER_JWT_PUBLIC_JWK, and checks four things:

  1. A token this key signed, with the reviewer issuer and audience, is accepted, and its
     subject comes back so the demo account can be resolved from it.
  2. A token with the reviewer issuer but signed by a DIFFERENT key is refused, not let
     through. This is the property that matters: without the private key nobody gets in.
  3. An expired reviewer token is refused.
  4. With no reviewer key configured, the path is off: a reviewer-looking token is not
     handled here, so production, which never sets the key, is unaffected.

    python3 tests/test_reviewer_auth.py
"""

import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import jwt
from cryptography.hazmat.primitives.asymmetric import ec


def _keypair():
    key = ec.generate_private_key(ec.SECP256R1())
    pub = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(key.public_key()))
    pub.update({"kid": "reviewer-test", "use": "sig", "alg": "ES256"})
    return key, json.dumps(pub)


def _token(key, *, iss="mse-reviewer", aud="mse-reviewer", sub="demo-subject",
           email="reviewer@example.com", exp_in=3600):
    return jwt.encode(
        {"iss": iss, "aud": aud, "sub": sub, "email": email, "emailVerified": True,
         "exp": int(time.time()) + exp_in},
        key, algorithm="ES256", headers={"kid": "reviewer-test"})


passed = failed = 0


def check(name, ok):
    global passed, failed
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    passed += ok
    failed += not ok


def main():
    key, pub = _keypair()
    other, _ = _keypair()
    os.environ["REVIEWER_JWT_PUBLIC_JWK"] = pub
    # Import after the key is set, so a fresh read of the environment is guaranteed.
    from app import auth
    from app.problems import Problem

    claims = auth.verify(_token(key))
    check("a valid reviewer token is accepted", claims.get("sub") == "demo-subject")
    check("its email survives for the account", claims.get("email") == "reviewer@example.com")

    try:
        auth.verify(_token(other))  # reviewer issuer, wrong key
        check("a token signed by another key is refused", False)
    except Problem as p:
        check("a token signed by another key is refused", p.status_code == 401)

    try:
        auth.verify(_token(key, exp_in=-10))
        check("an expired reviewer token is refused", False)
    except Problem as p:
        check("an expired reviewer token is refused", p.status_code == 401)

    # The path is off without the key: a reviewer-looking token is not handled here. verify()
    # then falls to the provider path, which this test does not configure, so assert on the
    # routing helper directly.
    del os.environ["REVIEWER_JWT_PUBLIC_JWK"]
    check("the path is off when no reviewer key is set", auth._verify_reviewer(_token(key)) is None)

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
