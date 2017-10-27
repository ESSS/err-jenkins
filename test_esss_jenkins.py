import pytest

from esss_jenkins import filter_jobs_by_factor_string


pytest_plugins = ["errbot.backends.test"]
extra_plugin_dir = '.'


@pytest.fixture
def testbot(testbot):
    from errbot.backends.test import TestPerson
    jenkins_plugin = testbot.bot.plugin_manager.get_plugin_obj_by_name('Jenkins')
    jenkins_plugin.config = {'JENKINS_URL': 'https://my-server.com/jenkins'}
    testbot.bot.sender = TestPerson('fry@localhost', nick='fry')
    return testbot


def test_jenkins_token(testbot):
    testbot.push_message('!jenkins token')
    response = testbot.pop_message()
    assert 'Jenkins API Token not configured' in response
    assert 'https://my-server.com/jenkins/user/fry/configure' in response

    testbot.push_message('!jenkins token secret-token')
    response = testbot.pop_message()
    assert response == 'Token saved.'

    testbot.push_message('!jenkins token')
    response = testbot.pop_message()
    assert response == 'You API Token is: secret-token'


def test_factors():
    jobs = [
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-win64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-win64g',
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-linux64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-calc-linux64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-synthetic-linux64',
        'alfasim-fb-ASIM-480-network-refactorings-part1-synthetic-linux64',
        "eden-fb-ASIM-483-remove-dummy-velocity-part5-linux64-27",
        "eden-fb-ASIM-483-remove-dummy-velocity-part5-win64-27",
        "eden-win64-27",
        "etk-rb-KRA-v2.5.0-win64-27",
        "etk-rb-KRA-v2.5.0-win64-35",
    ]

    assert filter_jobs_by_factor_string(jobs, 'ASIM-501 app win64'.split()) == [
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-win64',
    ]

    assert filter_jobs_by_factor_string(jobs, 'ASIM-501 app win64,linux64'.split()) == [
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-win64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-linux64',
    ]

    assert filter_jobs_by_factor_string(jobs, 'ASIM-501 win64,linux64'.split()) == [
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-win64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-linux64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-calc-linux64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-synthetic-linux64',
    ]

    assert filter_jobs_by_factor_string(jobs, ['eden-win64-27']) == [
        "eden-fb-ASIM-483-remove-dummy-velocity-part5-win64-27",
        "eden-win64-27",
    ]

    assert filter_jobs_by_factor_string(jobs, ['"eden-win64-27"']) == [
        "eden-win64-27",
    ]
