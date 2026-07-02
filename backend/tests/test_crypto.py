from app.services.crypto import decrypt, encrypt


def test_encrypt_decrypt_roundtrip():
    plaintext = "sk-volcano-abc123secret"
    ct = encrypt(plaintext)
    assert ct != plaintext
    assert decrypt(ct) == plaintext


def test_encrypt_produces_different_ciphertext():
    pt = "same-secret"
    assert encrypt(pt) != encrypt(pt)