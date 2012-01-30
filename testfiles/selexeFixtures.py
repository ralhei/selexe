

def setUp(wdc):
    wdc('open', '/pypi/pyRserve')


def tearDown(wdc):
    wdc('open', '/pypi/pyRserve')
