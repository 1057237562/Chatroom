#!/usr/bin/env python3
"""
SSL Certificate Generator for FastAPI Chatroom

Generates self-signed SSL certificates with Subject Alternative Names (SAN)
for local development and deployment.

Usage:
    python generate_cert.py                    # Use default IP
    python generate_cert.py --ip 192.168.1.100 # Specify custom IP
    python generate_cert.py --ips 127.0.0.1,192.168.1.100,example.com  # Multiple IPs/domains
"""

import argparse
import ipaddress
import os
import sys
from datetime import datetime, timedelta, timezone

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("Error: cryptography library not found.")
    print("Please install it with: pip install cryptography")
    sys.exit(1)


def generate_certificate(
    ips: list[str],
    domains: list[str],
    output_dir: str = ".",
    key_file: str = "key.pem",
    cert_file: str = "cert.pem",
    days_valid: int = 365,
    key_size: int = 2048,
) -> tuple[str, str]:
    """
    Generate a self-signed SSL certificate.
    
    Args:
        ips: List of IP addresses to include in SAN
        domains: List of domain names to include in SAN
        output_dir: Directory to save certificate files
        key_file: Name of the private key file
        cert_file: Name of the certificate file
        days_valid: Number of days the certificate is valid
        key_size: RSA key size in bits
    
    Returns:
        Tuple of (key_path, cert_path)
    """
    key_path = os.path.join(output_dir, key_file)
    cert_path = os.path.join(output_dir, cert_file)
    
    print(f"Generating {key_size}-bit RSA key...")
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print(f"Private key saved to: {key_path}")
    
    san_list = []
    san_list.append(x509.DNSName("localhost"))
    
    for domain in domains:
        if domain and domain != "localhost":
            san_list.append(x509.DNSName(domain))
    
    san_list.append(x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")))
    
    for ip in ips:
        if ip and ip != "127.0.0.1":
            try:
                san_list.append(x509.IPAddress(ipaddress.IPv4Address(ip)))
            except ipaddress.AddressValueError:
                print(f"Warning: Invalid IP address '{ip}', skipping...")
    
    common_name = ips[0] if ips else (domains[0] if domains else "localhost")
    
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Chatroom"),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    
    print(f"Generating certificate valid for {days_valid} days...")
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=days_valid))
        .add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        )
        .sign(key, hashes.SHA256(), default_backend())
    )
    
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print(f"Certificate saved to: {cert_path}")
    
    print("\nCertificate Details:")
    print(f"  Common Name: {common_name}")
    print(f"  Valid From: {cert.not_valid_before_utc}")
    print(f"  Valid Until: {cert.not_valid_after_utc}")
    print("  Subject Alternative Names:")
    for san in san_list:
        print(f"    - {san}")
    
    return key_path, cert_path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate self-signed SSL certificates for the Chatroom application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_cert.py
  python generate_cert.py --ip 192.168.1.100
  python generate_cert.py --ips 127.0.0.1,81.68.133.63 --domains localhost,example.com
  python generate_cert.py --output ./certs --days 730
        """
    )
    
    parser.add_argument(
        "--ip",
        type=str,
        default="81.68.133.63",
        help="Primary IP address for the certificate (default: 81.68.133.63)"
    )
    
    parser.add_argument(
        "--ips",
        type=str,
        help="Comma-separated list of IP addresses (e.g., 127.0.0.1,192.168.1.100)"
    )
    
    parser.add_argument(
        "--domains",
        type=str,
        default="localhost",
        help="Comma-separated list of domain names (default: localhost)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default=".",
        help="Output directory for certificate files (default: current directory)"
    )
    
    parser.add_argument(
        "--key-file",
        type=str,
        default="key.pem",
        help="Name of the private key file (default: key.pem)"
    )
    
    parser.add_argument(
        "--cert-file",
        type=str,
        default="cert.pem",
        help="Name of the certificate file (default: cert.pem)"
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Number of days the certificate is valid (default: 365)"
    )
    
    parser.add_argument(
        "--key-size",
        type=int,
        default=2048,
        choices=[1024, 2048, 4096],
        help="RSA key size in bits (default: 2048)"
    )
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    ips = []
    if args.ips:
        ips = [ip.strip() for ip in args.ips.split(",") if ip.strip()]
    else:
        ips = [args.ip]
    
    domains = [d.strip() for d in args.domains.split(",") if d.strip()]
    
    if not os.path.exists(args.output):
        os.makedirs(args.output)
        print(f"Created output directory: {args.output}")
    
    print("=" * 50)
    print("SSL Certificate Generator for Chatroom")
    print("=" * 50)
    
    key_path, cert_path = generate_certificate(
        ips=ips,
        domains=domains,
        output_dir=args.output,
        key_file=args.key_file,
        cert_file=args.cert_file,
        days_valid=args.days,
        key_size=args.key_size,
    )
    
    print("\n" + "=" * 50)
    print("Certificate generation completed!")
    print("=" * 50)
    print("\nNext steps:")
    print("1. Restart your FastAPI server to use the new certificate")
    print("2. For browsers, you may need to manually trust this certificate")
    print("   (it's self-signed, so browsers will show a security warning)")
    print("\nTo trust the certificate in Chrome:")
    print("  - Click 'Advanced' -> 'Proceed to <site> (unsafe)'")
    print("  - Or import cert.pem into your system's trusted root certificates")


if __name__ == "__main__":
    main()
