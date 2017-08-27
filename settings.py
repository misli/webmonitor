SENTRY_DSN = ''

host1_ipv4 = ['4.3.2.1']
host1_ipv6 = ['2001::1']
host2_ipv4 = ['4.3.2.2']
host2_ipv6 = ['2001::2']

host1 = host1_ipv4 + host1_ipv6
host2 = host2_ipv4 + host2_ipv6

both = host1 + host2

CHECKS = {
    # canonical urls checked every 60 seconds
    60: [
        ('https://www.mydomain.com/', both),
        ('https://shop.mydomain.com/', both),
        # test only runs on host1
        ('https://test.mydomain.com/', host1),
    ],
    # redirections checked every 600 seconds
    600: [
        ('http://www.mydomain.com/', both),
        ('//mydomain.com/', both),
        ('http://shop.mydomain.com/', both),
        ('http://test.mydomain.com/', host1),
    ],
}
