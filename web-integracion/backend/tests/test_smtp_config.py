"""No network: SMTP policy and explicit external file configuration."""
import json,os,tempfile
from pathlib import Path
from unittest.mock import patch
from django.test import SimpleTestCase,override_settings
from django.core.mail import EmailMessage
from cuentas.email import AuthorizedSMTPBackend,MailUnavailable,delivery_problem
from tools.correo_config import load_smtp_file

@override_settings(ELCHILITO_SMTP_ENABLED=True,EMAIL_HOST='smtp.example.test',EMAIL_PORT=587,
 EMAIL_HOST_USER='sender@example.test',EMAIL_HOST_PASSWORD='synthetic-for-mocked-smtp-only',
 EMAIL_USE_TLS=True,EMAIL_USE_SSL=False,EMAIL_TIMEOUT=10,
 ELCHILITO_SMTP_ALLOWED_RECIPIENTS=[])
class SMTPConfigurationTests(SimpleTestCase):
 @override_settings(ELCHILITO_SMTP_RECIPIENT_MODE='any-valid',EMAIL_BACKEND='cuentas.email.AuthorizedSMTPBackend')
 def test_public_registration_accepts_valid_addresses_without_network(self):
  for address in ['one@example.test','two@example.test']:
   self.assertIsNone(delivery_problem(address))
  self.assertIsNotNone(delivery_problem('not-an-email'))
  with patch('cuentas.email.SMTPBackend') as backend:
   backend.return_value.__enter__.return_value.send_messages.return_value=1
   self.assertEqual(AuthorizedSMTPBackend().send_messages([EmailMessage('Verificación','Prueba',to=['two@example.test'])]),1)
   self.assertTrue(backend.call_args.kwargs['use_tls'])
 @override_settings(ELCHILITO_SMTP_RECIPIENT_MODE='restricted',ELCHILITO_SMTP_ALLOWED_RECIPIENTS=['ONE@example.test'])
 def test_restricted_mode_is_still_enforced(self):
  with patch('cuentas.email.SMTPBackend') as backend:
   with self.assertRaises(MailUnavailable):AuthorizedSMTPBackend().send_messages([EmailMessage('Prueba','Prueba',to=['two@example.test'])])
   backend.assert_not_called()
 @override_settings(ELCHILITO_SMTP_RECIPIENT_MODE='any-valid')
 def test_public_mode_rejects_invalid_destination_before_connection(self):
  with patch('cuentas.email.SMTPBackend') as backend:
   with self.assertRaises(MailUnavailable):AuthorizedSMTPBackend().send_messages([EmailMessage('Prueba','Prueba',to=['bad'])])
   backend.assert_not_called()
 def test_external_configuration_requires_mode_0600_and_explicit_keys(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'smtp.json'
   data={'CHILITO_SMTP_ENABLED':'1','CHILITO_SMTP_HOST':'smtp.example.test','CHILITO_SMTP_PORT':'587',
    'CHILITO_SMTP_USER':'sender@example.test','CHILITO_SMTP_PASSWORD':'synthetic-only',
    'CHILITO_SMTP_RECIPIENT_MODE':'any-valid','CHILITO_SMTP_ALLOWED_RECIPIENTS':'','CHILITO_FROM_EMAIL':'sender@example.test'}
   p.write_text(json.dumps(data));p.chmod(0o600)
   self.assertEqual(load_smtp_file(p),data)
   p.chmod(0o644)
   with self.assertRaises(ValueError):load_smtp_file(p)
 @override_settings(ELCHILITO_SMTP_RECIPIENT_MODE='unknown')
 def test_invalid_policy_fails_closed(self):
  with self.assertRaises(MailUnavailable):AuthorizedSMTPBackend().send_messages([])
