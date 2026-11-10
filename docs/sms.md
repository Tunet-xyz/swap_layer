# SMS

Twilio and AWS SNS are implemented. Vonage and other SMS vendors are not selectable providers. Install `SwapLayer[sms]` for Twilio 9.x or `SwapLayer[aws]` for SNS.

```python
import os
from swap_layer import configure, get_provider
configure(communications={"sms": {"provider": "twilio", "twilio": {
    "account_sid": os.environ["TWILIO_ACCOUNT_SID"],
    "auth_token": os.environ["TWILIO_AUTH_TOKEN"],
    "from_number": os.environ["TWILIO_FROM_NUMBER"],
}}})
result = get_provider("sms").send_sms(to="+15555551234", message="Example")
```

Explicit Twilio configuration works without Django. Twilio requests time out after 30 seconds; pass `timeout=` to `TwilioSMSProvider` to change it. Use E.164 phone numbers and a test account/approved recipient before enabling real sends.

For SNS, configure `communications.sms={'provider':'sns','sns':{'region_name':'eu-west-2','sender_id':'Example'}}`. Credentials may be supplied through `aws_access_key_id`/`aws_secret_access_key` or boto3's normal IAM credential chain. The library does not supply an AWS account.

`send_sms` and `send_bulk_sms` use the selected adapter. Twilio also supplies message status/history and lookup/account operations; its `opt_out_number` and `opt_in_number` return the status `not_supported` and do not call Twilio, which applies STOP and START replies itself. SNS delivery-status lookup returns `unknown`, message history returns an empty list, and balance is unavailable; those are documented placeholders rather than live monitoring. SNS opt-out queries and opt-in calls use AWS APIs. Phone validation is provider-dependent (SNS validates with the provider's own AWS settings) and is not proof of ownership.

Applications implement messaging consent, opt-out policy, rate limits, OTP verification, and abuse controls. A provider change does not migrate phone numbers or suppression lists. Calls can incur charges against the caller's account. MCP test sends require client approval.

Django model/admin helpers are in `swap_layer.communications.sms.models` and `.admin` and require your application's concrete models and migrations.
