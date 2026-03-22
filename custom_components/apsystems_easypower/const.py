"""Constants for AP Systems EasyPower integration."""

DOMAIN = "apsystems_easypower"

# API
API_BASE_URL = "https://app.api.apsystemsema.com:9223"
API_APP_ID = "4029817264d4821d0164d4821dd80015"
API_APP_SECRET = "EZAd2023"

# RSA public key for credential encryption (extracted from APK)
RSA_PUBLIC_KEY_B64 = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAgdwBhVodMQ84lYZhDSGO"
    "UDQAks+NMa7WQ83mR1OyHiIWtZ1wWAh4H7fclkdNS3lWCmDH9ldF7Kf6JlEvZTc0"
    "Textv+YMLXO2gdDIoBvg7vlhY4HxOjXUIFQ+s7cWRrmEIgVVnTBLZU1GMC8zld7W"
    "H9v9EYCAqK7rvGJP0STZ/g6BP8RGJKhdpY6b+ndMXRUBYwkqy8m1SDJHm1FeHSLQ"
    "WTaWbP5pz1yrGkkwvx+pib6wli+WE70/uPHp0zXZK5iUwmRQfOkTjDOGJyEE1dqk"
    "fHDTqne5ED81M4fCIEFYhyvnr1rifVJKHCDRGYQpJ0CiffjjH1ZOGSIN4JPG1EEIj"
    "QIDAQAB"
)

# Config entry keys
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Data keys
DATA_COORDINATOR = "coordinator"

# Update interval (seconds)
UPDATE_INTERVAL = 300  # 5 minutes
