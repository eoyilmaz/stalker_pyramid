# -*- coding: utf-8 -*-
import unittest

from pyramid import testing


class ClientViewTests(unittest.TestCase):
    """client tests
    """
    config = {
        'sqlalchemy.url':
            'postgresql://stalker_admin:stalker@localhost/stalker_test'
    }

    def setUp(self):
        """set up the test
        """
        from stalker import db
        testing.setUp()
        db.setup(self.config)
        db.init()

    def tearDown(self):
        """clear the test
        """
        from stalker import db
        from stalker.db.declarative import Base
        db.setup(self.config)

        connection = db.DBSession.connection()
        engine = connection.engine
        connection.close()
        Base.metadata.drop_all(engine)
        db.DBSession.remove()

        testing.tearDown()

    def test_get_report_template_is_working_properly(self):
        """testing if get_report_template() will return proper data from
        the given client
        """
        # generate test data
        from stalker import Client
        c = Client(name='Test Client')

        import json

        report_template = {
            'name': 'Reklam Verenler Dernegi',
            'template': {
                'path': '/path/to/the/excel/file.xlsx'
            },
            'mapper': {
                'sheets': [
                    {
                        'name': 'sheet1',
                        'cells': {
                            'A1': [
                                {
                                    'query': {
                                        'name': 'Modeller'
                                    },
                                    'result': '{item.price}'
                                }
                            ]
                        }
                    },
                    {
                        'name': 'sheet2',
                        'cells': {
                            'A32': [
                                {
                                    'query': {
                                        'name': 'Animation Director'
                                    },
                                    'result': '{item.price}'
                                },
                                {
                                    'query': {
                                        'name': 'Animator'
                                    },
                                    'result': '{item.price}'
                                },
                            ]
                        }
                    }
                ]
            }
        }

        generic_text = {
            'some_other_data': 1,
            'some_extra_data': 2,
            'report_template': report_template
        }
        c.generic_text = json.dumps(generic_text)

        from stalker_pyramid.views import client
        result = client.get_report_template(c)
        self.assertEqual(
            result, report_template
        )

    def test_get_report_template_with_client_with_no_generic_text_value(self):
        """testing if get_report_template() will return None if the
        client has no report_template defined
        """
        # generate test data
        from stalker import Client
        c = Client(name='Test Client')

        from stalker_pyramid.views.client import get_report_template
        self.assertIsNone(get_report_template(c))

    def test_get_report_template_with_non_client_instance(self):
        """testing if a TypeError will be raised when the client argument value
        is not a stalker.Client instance
        """
        from stalker_pyramid.views.client import get_report_template
        with self.assertRaises(TypeError) as cm:
            get_report_template('not a client instance')

        self.assertEqual(
            str(cm.exception),
            'Please supply a proper stalker.models.client.Client instance for '
            'the client argument and not a str'
        )

    def test_generate_report_with_a_project_with_no_client(self):
        """testing if the generate_report() will raise a RuntimeError if the
        project doesn't have a client
        """
        from stalker import Client, Budget, Project, Status, StatusList
        project = Project(
            name='Test Project',
            code='TP',
            status_list=StatusList(
                name='Test Status List',
                target_entity_type='Project',
                statuses=[Status(name='sts1', code='sts1')]
            )
        )
        b = Budget(
            name='Test Budget',
            project=project
        )
        from stalker_pyramid.views.client import generate_report
        with self.assertRaises(RuntimeError) as cm:
            generate_report(b)

        self.assertEqual(
            str(cm.exception),
            'The Project has no client, please specify the client of this '
            'project in ``Project.client`` attribute!!'
        )

    def test_generate_report_with_a_client_with_no_report_template(self):
        """testing if the generate_report() will raise a RuntimeError if the
        client doesn't have a report_format
        """
        from stalker import Client, Budget, Project, Status, StatusList
        c = Client(name='Some Client')
        project = Project(
            name='Test Project',
            code='TP',
            status_list=StatusList(
                name='Test Status List',
                target_entity_type='Project',
                statuses=[Status(name='sts1', code='sts1')]
            ),
            client=c
        )
        b = Budget(
            name='Test Budget',
            project=project
        )
        from stalker_pyramid.views.client import generate_report
        with self.assertRaises(RuntimeError) as cm:
            generate_report(b)

        self.assertEqual(
            str(cm.exception),
            'The Client has no report_template, please define a '
            '"report_template" value in the Client.generic_text attribute '
            'with proper format (see documentation for the report_template '
            'format)!'
        )

    def test_generate_report_with_budget_argument_is_not_a_budget_instance(self):
        """testing if a TypeError will be raised when the budget argument is
        not a proper stalker.Budget instance
        """
        from stalker_pyramid.views.client import generate_report
        with self.assertRaises(TypeError) as cm:
            generate_report('this is not a budget')

        self.assertEqual(
            str(cm.exception),
            'Please supply a proper ``stalker.model.budget.Budget`` instance '
            'for the ``budget`` argument and not str'
        )

    def test_generate_report_is_working_properly(self):
        """testing if the generate_report() is working properly
        """
        import os
        from stalker import db, Client
        c = Client(name='Some Client')

        # generate the template
        report_template = {
            'name': 'Reklam Verenler Dernegi',
            'template': {
                'path': os.path.abspath('./tests/test_data/report_template.xlsx')
            },
            'mapper': {
                'sheets': [
                    {
                        'name': 'Sheet1',
                        'cells': {
                            'B2': [
                                {
                                    'query': {
                                        'name': 'Modeler'
                                    },
                                    'result': '{item.price}'
                                }
                            ],
                            'B3': [
                                {
                                    'query': {
                                        'name': 'Director'
                                    },
                                    'result': '{item.price}'
                                }
                            ],
                            'B4': [
                                {
                                    'query': {
                                        'name': 'Assistant Director'
                                    },
                                    'result': '{item.price}'
                                }
                            ],
                        }
                    },
                    {
                        'name': 'Sheet2',
                        'cells': {
                            'B2': [
                                {
                                    'query': {
                                        'name': 'Animation Director'
                                    },
                                    'result': '{item.price} + {item.price} * {item.stoppage_ratio}'
                                },
                                {
                                    'query': {
                                        'name': 'Animator'
                                    },
                                    'result': '{item.price}'
                                },
                            ]
                        }
                    }
                ]
            }
        }

        generic_text_data = {
            'some values': 1,
            'some other values': 'some text',
            'report_template': report_template
        }

        # store the template
        import json
        c.generic_text = json.dumps(generic_text_data)

        # store the client
        db.DBSession.add(c)
        db.DBSession.commit()

        # create a Project
        from stalker import Repository, Project, Status, StatusList
        repo = Repository(
            name='Test Repository',
            windows_path='c:/test',
            linux_path='/tmp/test',
            osx_path='/tmp/test'
        )
        db.DBSession.add(repo)

        status1 = Status(
            name='Work In Progress',
            code='WIP'
        )

        status2 = Status(
            name='Completed',
            code='CMPL'
        )
        db.DBSession.add_all([status1, status2])

        project_status_list = StatusList(
            name='Project Status List',
            target_entity_type='Project',
            statuses=[status1, status2]
        )
        db.DBSession.add(project_status_list)
        db.DBSession.commit()

        p = Project(
            name='Test Project 1',
            code='TP1',
            client=c,
            repositories=[repo],
            status_list=project_status_list
        )
        db.DBSession.add(p)
        db.DBSession.commit()

        # create a budget
        from stalker import Budget, BudgetEntry, Good
        b1 = Budget(
            name='Test Budget 1',
            project=p
        )

        # create some goods and entries
        # Modeler
        g1 = Good(
            name='Modeler',
            cost=100,
            msrp=80,
            unit='h'
        )
        db.DBSession.add(g1)

        be1 = BudgetEntry(
            name='Modeler',
            budget=b1,
            good=g1,
            price=150,
            amount=4
        )
        db.DBSession.add(be1)

        # Animation Director
        g2 = Good(
            name='Animation Director',
            cost=150,
            msrp=125,
            unit='h'
        )
        db.DBSession.add(g2)

        be2 = BudgetEntry(
            name='Animation Director',
            budget=b1,
            good=g2,
            amount=4,
            price=g2.cost * 4
        )
        # add stoppage ratio
        import json
        be2.generic_text = json.dumps({'stoppage_ratio': 0.25})
        db.DBSession.add(be2)

        # Director
        g3 = Good(
            name='Director',
            cost=150,
            msrp=125,
            unit='h'
        )
        db.DBSession.add(g3)

        be3 = BudgetEntry(
            name='Director',
            budget=b1,
            good=g3,
            amount=5,
            price=g3.cost * 5
        )
        db.DBSession.add(be3)

        # Assistant Director
        g4 = Good(
            name='Assistant Director',
            cost=70,
            msrp=50,
            unit='h'
        )
        db.DBSession.add(g4)

        be4 = BudgetEntry(
            name='Assistant Director',
            budget=b1,
            good=g4,
            amount=12,
            price=g4.cost * 12
        )
        db.DBSession.add(be4)

        # Animator
        g5 = Good(
            name='Animator',
            cost=25,
            msrp=20,
            unit='h'
        )
        db.DBSession.add(g5)

        be5 = BudgetEntry(
            name='Animator',
            budget=b1,
            good=g5,
            amount=120,
            price=g5.cost * 120
        )
        db.DBSession.add(be5)
        db.DBSession.commit()

        # ok we got the test data ready
        # now request the get_report() method to do its job
        from stalker_pyramid.views.client import generate_report
        import tempfile
        output_file_location = tempfile.mktemp(suffix='.xlsx')

        generate_report(
            budget=b1,
            output_path=output_file_location
        )

        # read the result file as an XLSX file
        import openpyxl
        wb = openpyxl.load_workbook(output_file_location)

        # check sheet names
        self.assertEqual(
            wb.get_sheet_names(),
            ['Sheet1', 'Sheet2']
        )

        # check the first sheet1
        sh1 = wb['Sheet1']

        # modeler price
        self.assertEqual(
            sh1['B2'].value,
            be1.price

        )

        # Director Price
        self.assertEqual(
            sh1['B3'].value,
            be3.price
        )

        # Assistant Director Price
        self.assertEqual(
            sh1['B4'].value,
            be4.price
        )

        # check the second sheet
        sh2 = wb['Sheet2']

        # Animation Director + Animator
        self.assertEqual(
            sh2['B2'].value,
            be2.price + be2.price * 0.25 + be5.price
        )

    def test_generate_report_output_path_argument_is_skipped(self):
        """testing if the generate_report() will generate a temp file path
        and return it when the output_path is '' or skipped
        """
        import os
        from stalker import db, Client
        c = Client(name='Some Client')

        # generate the template
        report_template = {
            'name': 'Reklam Verenler Dernegi',
            'template': {
                'path': os.path.abspath('./tests/test_data/report_template.xlsx')
            },
            'mapper': {
                'sheets': [
                    {
                        'name': 'Sheet1',
                        'cells': {
                            'B2': [
                                {
                                    'query': {
                                        'name': 'Modeler'
                                    },
                                    'result': '{item.price}'
                                }
                            ],
                            'B3': [
                                {
                                    'query': {
                                        'name': 'Director'
                                    },
                                    'result': '{item.price}'
                                }
                            ],
                            'B4': [
                                {
                                    'query': {
                                        'name': 'Assistant Director'
                                    },
                                    'result': '{item.price}'
                                }
                            ],
                        }
                    },
                    {
                        'name': 'Sheet2',
                        'cells': {
                            'B2': [
                                {
                                    'query': {
                                        'name': 'Animation Director'
                                    },
                                    'result': '{item.price} + {item.price} * {item.stoppage_ratio}'
                                },
                                {
                                    'query': {
                                        'name': 'Animator'
                                    },
                                    'result': '{item.price}'
                                },
                            ]
                        }
                    }
                ]
            }
        }

        generic_text_data = {
            'some values': 1,
            'some other values': 'some text',
            'report_template': report_template
        }

        # store the template
        import json
        c.generic_text = json.dumps(generic_text_data)

        # store the client
        db.DBSession.add(c)
        db.DBSession.commit()

        # create a Project
        from stalker import Repository, Project, Status, StatusList
        repo = Repository(
            name='Test Repository',
            windows_path='c:/test',
            linux_path='/tmp/test',
            osx_path='/tmp/test'
        )
        db.DBSession.add(repo)

        status1 = Status(
            name='Work In Progress',
            code='WIP'
        )

        status2 = Status(
            name='Completed',
            code='CMPL'
        )
        db.DBSession.add_all([status1, status2])

        project_status_list = StatusList(
            name='Project Status List',
            target_entity_type='Project',
            statuses=[status1, status2]
        )
        db.DBSession.add(project_status_list)
        db.DBSession.commit()

        p = Project(
            name='Test Project 1',
            code='TP1',
            client=c,
            repositories=[repo],
            status_list=project_status_list
        )
        db.DBSession.add(p)
        db.DBSession.commit()

        # create a budget
        from stalker import Budget, BudgetEntry, Good
        b1 = Budget(
            name='Test Budget 1',
            project=p
        )

        # create some goods and entries
        # Modeler
        g1 = Good(
            name='Modeler',
            cost=100,
            msrp=80,
            unit='h'
        )
        db.DBSession.add(g1)

        be1 = BudgetEntry(
            name='Modeler',
            budget=b1,
            good=g1,
            price=150,
            amount=4
        )
        db.DBSession.add(be1)

        # Animation Director
        g2 = Good(
            name='Animation Director',
            cost=150,
            msrp=125,
            unit='h'
        )
        db.DBSession.add(g2)

        be2 = BudgetEntry(
            name='Animation Director',
            budget=b1,
            good=g2,
            amount=4,
            price=g2.cost * 4
        )
        # add stoppage ratio
        import json
        be2.generic_text = json.dumps({'stoppage_ratio': 0.25})
        db.DBSession.add(be2)

        # Director
        g3 = Good(
            name='Director',
            cost=150,
            msrp=125,
            unit='h'
        )
        db.DBSession.add(g3)

        be3 = BudgetEntry(
            name='Director',
            budget=b1,
            good=g3,
            amount=5,
            price=g3.cost * 5
        )
        db.DBSession.add(be3)

        # Assistant Director
        g4 = Good(
            name='Assistant Director',
            cost=70,
            msrp=50,
            unit='h'
        )
        db.DBSession.add(g4)

        be4 = BudgetEntry(
            name='Assistant Director',
            budget=b1,
            good=g4,
            amount=12,
            price=g4.cost * 12
        )
        db.DBSession.add(be4)

        # Animator
        g5 = Good(
            name='Animator',
            cost=25,
            msrp=20,
            unit='h'
        )
        db.DBSession.add(g5)

        be5 = BudgetEntry(
            name='Animator',
            budget=b1,
            good=g5,
            amount=120,
            price=g5.cost * 120
        )
        db.DBSession.add(be5)
        db.DBSession.commit()

        # ok we got the test data ready
        # now request the get_report() method to do its job
        from stalker_pyramid.views.client import generate_report
        import tempfile
        output_file_location = tempfile.mktemp(suffix='.xlsx')

        output_file_location = generate_report(
            budget=b1
        )

        self.assertTrue(tempfile.gettempdir() in output_file_location)
        self.assertTrue('.xlsx' in output_file_location)

    def test_get_distinct_report_templates_is_working_properly_with_client_that_doesnt_have_a_report_template(self):
        """testing if get_distinct_report_templates() gathers templates from
        all clients in the database
        """
        from stalker import db, Client
        import json

        # Client 1
        c1 = Client(
            name='Client1'
        )

        report_template1 = {
            'name': 'Report1',
            'template': {'path': '/some/path'},
            'mapper': {}
        }

        c1.generic_text = json.dumps(
            {
                'report_template': report_template1
            }
        )

        db.DBSession.add(c1)

        # Client 2
        c2 = Client(
            name='Client2'
        )

        c2.generic_text = json.dumps(
            {
                'report_template': report_template1
            }
        )

        db.DBSession.add(c2)

        # Client 3
        c3 = Client(
            name='Client3'
        )

        report_template2 = {'name': 'Report2', 'template': {'path': '/some/path'},
                   'mapper': {}}
        c3.generic_text = json.dumps(
            {
                'report_template': report_template2
            }
        )

        db.DBSession.add(c3)

        # Client 4
        c4 = Client(
            name='Client4'
        )

        report_template3 = {
            'name': 'Report3',
            'template': {'path': '/some/path'},
            'mapper': {}
        }

        c4.generic_text = json.dumps(
            {
                'report_template': report_template3
            }
        )
        db.DBSession.add(c4)

        # Client 5 - with no report template
        c5 = Client(
            name='Client5'
        )

        db.DBSession.add(c5)
        db.DBSession.commit()

        from stalker_pyramid.views.client import get_distinct_report_templates

        result = get_distinct_report_templates()

        self.maxDiff = None
        self.assertEqual(
            result,
            [report_template1, report_template2, report_template3]
        )

    def test_get_report_template_by_name_is_working_properly(self):
        """testing if get_report_template_by_name() is working properly
        """
        from stalker import db, Client
        import json

        # Client 1
        c1 = Client(
            name='Client1'
        )

        report_template1 = {
            'name': 'Report1',
            'template': {'path': '/some/path'},
            'mapper': {}
        }

        c1.generic_text = json.dumps(
            {
                'report_template': report_template1
            }
        )

        db.DBSession.add(c1)

        # Client 2
        c2 = Client(
            name='Client2'
        )

        c2.generic_text = json.dumps(
            {
                'report_template': report_template1
            }
        )

        db.DBSession.add(c2)

        # Client 3
        c3 = Client(
            name='Client3'
        )

        report_template2 = {'name': 'Report2',
                            'template': {'path': '/some/path'},
                            'mapper': {}}
        c3.generic_text = json.dumps(
            {
                'report_template': report_template2
            }
        )

        db.DBSession.add(c3)

        # Client 4
        c4 = Client(
            name='Client4'
        )

        report_template3 = {
            'name': 'Report3',
            'template': {'path': '/some/path'},
            'mapper': {}
        }

        c4.generic_text = json.dumps(
            {
                'report_template': report_template3
            }
        )

        db.DBSession.add(c4)

        # Client 5
        c5 = Client(
            name='Client5'
        )

        db.DBSession.add(c5)
        db.DBSession.commit()

        from stalker_pyramid.views.client import get_report_template_by_name

        result = get_report_template_by_name('Report1')

        self.maxDiff = None
        self.assertEqual(
            result,
            report_template1
        )

