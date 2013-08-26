

def setUp(sd):
    """Preparational steps for unit test execution.
    @args sd: selenium-driver instance
    """
    sd('open', '/static/setUpTearDown')


def tearDown(sd):
    """Finalization step after unittest has finished.
    @args sd: selenium-driver instance
    """
    sd('open', '/static/setUpTearDown')
