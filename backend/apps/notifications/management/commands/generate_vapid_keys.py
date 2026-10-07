"""Print a new VAPID key pair for Web Push (put them into .env)."""

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from django.core.management.base import BaseCommand
from py_vapid import Vapid, b64urlencode


class Command(BaseCommand):
    help = "Generate VAPID keys for Web Push."

    def handle(self, *args, **options):
        vapid = Vapid()
        vapid.generate_keys()
        private = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
        public = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        self.stdout.write(f"VAPID_PUBLIC_KEY={b64urlencode(public)}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={b64urlencode(private)}")
