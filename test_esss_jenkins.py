import pytest

from esss_jenkins import filter_jobs_by_find_string


pytest_plugins = ["errbot.backends.test"]
extra_plugin_dir = '.'


@pytest.fixture
def testbot(testbot):
    from errbot.backends.test import TestPerson
    testbot.bot.sender = TestPerson('fry@localhost', nick='fry')
    return testbot


@pytest.fixture(autouse=True)
def jenkins_plugin(testbot):
    jenkins_plugin = testbot.bot.plugin_manager.get_plugin_obj_by_name('Jenkins')
    jenkins_plugin.config = {
        'JENKINS_URL': 'https://my-server.com/jenkins',
        'JENKINS_TOKEN': 'jenkins-secret-token',
        'JENKINS_USERNAME': 'jenkins-user',

        'ROCKETCHAT_USER': 'rocketchat-user',
        'ROCKETCHAT_PASSWORD': 'rocketchat-secret-password',
        'ROCKETCHAT_DOMAIN': 'https://my-server.com/rocketchat',
    }
    return jenkins_plugin


def test_token(testbot):
    testbot.push_message('!jenkins token')
    response = testbot.pop_message()
    assert 'Jenkins API Token not configured' in response
    assert 'https://my-server.com/jenkins/user/fry/configure' in response

    testbot.push_message('!jenkins token secret-token')
    response = testbot.pop_message()
    assert response == 'Token saved.'

    testbot.push_message('!jenkins token')
    response = testbot.pop_message()
    assert response == 'You API Token is: secret-token (user: fry)'


def test_build_alias(testbot):
    from unittest.mock import patch
    
    testbot.push_message('!jenkins buildalias')
    response = testbot.pop_message()
    assert 'Pass alias name, some search keywords, and an optional set of parameters' in response

    testbot.push_message('!jenkins buildalias rr30l rocky30 linux --parameters=EXT=20')
    response = testbot.pop_message()
    assert 'Alias registered: rr30l' in response

    testbot.push_message('!jenkins buildalias')
    response = testbot.pop_message()
    assert 'Existing aliases' in response
    assert 'rr30l' in response

    testbot.push_message('!jenkins token secret-token')
    response = testbot.pop_message()
    assert response == 'Token saved.'
    
    jenkins_bot = testbot.bot.plugin_manager.get_plugin_obj_by_name('Jenkins')

    with patch.object(jenkins_bot, '_find_all_job_names_filtered') as job_names:
        job_names.return_value = []
        testbot.push_message('!jenkins build rr30l')
        response = testbot.pop_message()
        assert job_names.call_count == 1
        assert "No job found with pattern: ['rocky30', 'linux']" == response
        
        testbot.push_message('!jenkins build rr30l 6666')
        response = testbot.pop_message()
        assert job_names.call_count == 2
        assert "No job found with pattern: ['rocky30', 'linux', '6666']" == response

        job_names.return_value = ['job_1', 'job_2']
        testbot.push_message('!jenkins build rr30l 6666')
        response = testbot.pop_message()
        assert job_names.call_count == 3
        assert "Multiple jobs found with pattern" in response

        job_names.return_value = ['job_1']
        with patch.object(jenkins_bot, '_post_jenkins_json_request') as post_request:
            testbot.push_message('!jenkins build rr30l 6666')
            response = testbot.pop_message()

            assert job_names.call_count == 4
            assert post_request.call_count == 1
            assert post_request.call_args[0][0].endswith('buildWithParameters?{}'.format('EXT=20'))
            assert post_request.call_args[0][1] == 'fry'
            assert "Triggered 1 jobs:" in response


def test_webhook(jenkins_plugin, mocker):
    import rocketchat.api
    mocker.patch.object(rocketchat.api.RocketChatAPI, 'send_message', autospec=True)

    class DummyRequest:
        pass

    request = DummyRequest()
    request.params = {
        'number': '2',
        'job_name': 'fett-master-linux64',
        'timestamp': '1508516240981',
        'builtOn': 'dev-ubuntu16.04-linux-sv01-ci01',
        'event': 'jenkins.job.started',
        'userId': 'fry',
        'url': 'job/fett-master-linux64/2/',
     }
    jenkins_plugin.jenkins(request)
    args, kwargs = rocketchat.api.RocketChatAPI.send_message.call_args
    assert kwargs == {}
    _, text, user = args
    assert 'Job Started' in text
    assert '[fett-master-linux64](https://my-server.com/jenkins/job/fett-master-linux64/2/)' in text
    assert user == '@fry'


def test_find_string_basic():
    assert filter_jobs_by_find_string(JOBS, 'ASIM-501 app win64,linux64'.split()) == [
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-win64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-linux64',
    ]


@pytest.mark.parametrize('tr', [str.lower, str.upper, lambda x: x])
def test_find_string_case_sensitive(tr):
    assert filter_jobs_by_find_string(JOBS, tr('ASIM-501 app win64').split()) == [
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-win64',
    ]

    assert filter_jobs_by_find_string(JOBS, tr('ASIM-501 app win64,linux64').split()) == [
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-win64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-linux64',
    ]

    assert filter_jobs_by_find_string(JOBS, tr('ASIM-501 win64,linux64').split()) == [
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-win64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-linux64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-calc-linux64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-synthetic-linux64',
    ]

    assert filter_jobs_by_find_string(JOBS, [tr('eden-win64-27')]) == [
        "eden-fb-ASIM-483-remove-dummy-velocity-part5-win64-27",
        "eden-win64-27",
    ]

    assert filter_jobs_by_find_string(JOBS, [tr('"eden-win64-27"')]) == [
        "eden-win64-27",
    ]



def test_find_string_long_glob():
    assert filter_jobs_by_find_string(JOBS, '"*rb*kra*"'.split()) == [
        "etk-rb-KRA-v2.5.0-win64-27",
        "etk-rb-KRA-v2.5.0-win64-35",
    ]


def test_find_string_glob():
    assert filter_jobs_by_find_string(JOBS, 'network-refacto*'.split()) == [
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-win64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-win64g',
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-linux64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-calc-linux64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-synthetic-linux64',
        'alfasim-fb-ASIM-480-network-refactorings-part1-synthetic-linux64',
    ]

    assert filter_jobs_by_find_string(JOBS, 'network-refacto* win64,linux*'.split()) == [
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-win64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-linux64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-calc-linux64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-synthetic-linux64',
        'alfasim-fb-ASIM-480-network-refactorings-part1-synthetic-linux64',
    ]
    assert filter_jobs_by_find_string(JOBS, 'network-refacto* linux*'.split()) == [
        'alfasim-fb-ASIM-501-network-refactorings-part1-app-linux64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-calc-linux64',
        'alfasim-fb-ASIM-501-network-refactorings-part1-synthetic-linux64',
        'alfasim-fb-ASIM-480-network-refactorings-part1-synthetic-linux64',
    ]

    assert filter_jobs_by_find_string(JOBS, 'simbr network-refacto* win64,linux*'.split()) == []


JOBS = [
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
