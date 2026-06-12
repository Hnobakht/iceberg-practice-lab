## Security note:

This certificate is dummy and can be used for practice purposes. However i recommend to create your own using the following bash commands. I am not using it myself!

```bash
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout ./certs/k3s/server.key \
  -out ./certs/k3s/server.crt \
  -days 365 \
  -subj "/CN=k3s" \
  -addext "subjectAltName=DNS:k3s,IP:127.0.0.1"
```