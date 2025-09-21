from utilities import settings

GCP_OCR_CRED: dict = {
  "type": settings.TYPE,
  "project_id": settings.PROJECT_ID,
  "private_key_id":settings.PRIVATE_KEY_ID,
  "private_key": settings.PRIVATE_KEY,
  "client_id": settings.CLIENT_ID,
  "client_email":settings.CLIENT_EMAIL,
  "auth_uri": settings.AUTH_URI,
  "token_uri": settings.TOKEN_URI,
  "auth_provider_x509_cert_url": settings.AUTH_PROVIDER_X509_CERT_URL,
  "client_x509_cert_url": settings.CLIENT_X509_CERT_URL,
  "universe_domain": settings.UNIVERSE_DOMAIN
}
