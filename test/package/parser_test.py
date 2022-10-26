import unittest
import random

import qy.package as package


class TestRequirementVersionConstraintParser(unittest.TestCase):
    fake_package_json_path = "FAKE/qy-package.json5"
    fake_requirement_desc = "FAKE/requirement_desc"
    fake_version_constraint_index = 0
    fake_version_constraint_count = 0

    #
    # TODO: finish testing this module
    #

    #
    # Requirement version constraints: e.g. >=0.0.0, =1.0.0, <3.14.5
    #

    def test_parse_exact_requirement_version_constraint_string(self):
        component_count_iterator = range(
            package.Version.min_component_count, 
            package.Version.min_component_count + 1
        )
        for test_component_count in component_count_iterator:
            version_point = self.gen_dummy_version_point(test_component_count)
            rvc_string = "=" + str(version_point)
            rvc = package.parse_requirement_version_constraint_string(
                self.fake_package_json_path, 
                rvc_string,
                self.fake_requirement_desc,
                self.fake_version_constraint_index,
                self.fake_version_constraint_count
            )
            self.assertIsInstance(rvc, package.ExactVersionConstraint)
            self.assertEqual(rvc.point, version_point)

    def test_parse_relative_requirement_version_constraint_string(self):
        component_count_iterator = range(
            package.Version.min_component_count, 
            package.Version.min_component_count + 1
        )
        rel_operator_type_map = {
            '<': (package.MaxVersionConstraint, False), 
            '>': (package.MinVersionConstraint, False), 
            '<=': (package.MaxVersionConstraint, True), 
            '>=': (package.MinVersionConstraint, True)
        }
        for rel_operator, (rvc_type, is_closed) in rel_operator_type_map.items():
            for test_component_count in component_count_iterator:
                version_point = self.gen_dummy_version_point(test_component_count)
                rvc_string = rel_operator + str(version_point)
                parsed_rvc = package.parse_requirement_version_constraint_string(
                    self.fake_package_json_path, rvc_string,
                    self.fake_requirement_desc,
                    self.fake_version_constraint_index, 
                    self.fake_version_constraint_count
                )
                self.assertIsInstance(parsed_rvc, rvc_type)
                self.assertEqual(parsed_rvc.closed, is_closed)

    #
    # Helpers
    #

    @staticmethod
    def gen_dummy_version_point(component_count):
        return package.Version.from_components([
            random.randint(0, (1<<8)-1)
            for _ in range(component_count)
        ])


if __name__ == '__main__':
    unittest.main()
    
