from esss_jenkins import filter_jobs_by_factor_string


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
