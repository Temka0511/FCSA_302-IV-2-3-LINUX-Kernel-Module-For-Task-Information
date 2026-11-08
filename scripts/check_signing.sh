#!/usr/bin/env bash
# Check the Manual's certificate/sign-file steps without enrolling a machine key.
set -euo pipefail
cd "$(dirname "$0")/.."
kernel_dir=${KDIR:-/lib/modules/$(uname -r)/build}
test -x "$kernel_dir/scripts/sign-file"
test -f src/kernel/taskgraph.ko
sign_dir=$(mktemp -d)
trap 'rm -rf "$sign_dir"' EXIT
openssl req -new -x509 -newkey rsa:2048 -nodes \
  -days 3650 -subj "/CN=TaskGraph module/" \
  -addext "extendedKeyUsage=codeSigning,1.3.6.1.4.1.2312.16.1.2" \
  -keyout "$sign_dir/MOK.priv" \
  -outform DER -out "$sign_dir/MOK.der" >/dev/null 2>&1
chmod 600 "$sign_dir/MOK.priv"
cp src/kernel/taskgraph.ko "$sign_dir/taskgraph-signed.ko"
"$kernel_dir/scripts/sign-file" sha256 \
  "$sign_dir/MOK.priv" "$sign_dir/MOK.der" "$sign_dir/taskgraph-signed.ko"
openssl x509 -inform DER -in "$sign_dir/MOK.der" -noout -text |
  grep -q 'Code Signing'
tail -c 28 "$sign_dir/taskgraph-signed.ko" | grep -a -q '~Module signature appended~'
printf '%s\n' 'MOK certificate: code signing EKU OK' \
  'Kernel module copy: signature appended OK' \
  'UEFI enrollment and Secure Boot loading require a separate VM test.'
