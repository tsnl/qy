"""
Areas for improvement:
- check error handling on invalid input
"""

import unittest
import random

import qy.package as package
from qy.package.version_constraint import ExactVersionConstraint


class TestPackageParser(unittest.TestCase):
    fake_package_json_path = "FAKE/qy-package.json5"
    fake_package_description = "A fake package JSON object used for testing"
    fake_requirement_desc = "FAKE/requirement_desc"
    fake_git_requirement_location = "FAKE/git_repo_requirement.git"
    fake_filesystem_requirement_location = "FAKE/filesystem_package_requirement"
    fake_context_desc = "FAKE/generic_context_desc"
    fake_author = "Stephen J. Fry"
    fake_version_constraint_index = 0
    fake_version_constraint_count = 0

    #
    # Package
    #

    def test_package(self):
        vp0 = self.gen_dummy_version_point()
        vp1 = self.gen_dummy_version_point()
        p = package.parse_from_json_object(
            self.fake_package_json_path,
            {
                "author": self.fake_author,
                "description": self.fake_package_description,
                "version": str(vp0),
                "requires": [
                    {
                        "provider": "git",
                        "location": self.fake_git_requirement_location,
                        "version": str(vp1)
                    }
                ]
            }    
        )
        self.assertIsInstance(p, package.Package)
        self.assertEqual(p.author, self.fake_author)
        self.assertEqual(p.description, self.fake_package_description)
        self.assertEqual(p.version, vp0)
        self.assertEqual(len(p.requirements), 1)
        requirement = p.requirements[0]
        self.assertIsInstance(requirement, package.GitRequirement)
        self.assertEqual(requirement.provider, "git")
        self.assertEqual(requirement.location, self.fake_git_requirement_location)
        self.assertEqual(len(requirement.version_constraints), 1)
        self.assertEqual(requirement.version_constraints[0], ExactVersionConstraint(vp1))

    #
    # Version
    #

    def test_version(self):
        component_count_iterator = range(
            package.Version.min_component_count, 
            package.Version.max_component_count + 1
        )
        for component_count in component_count_iterator:
            v0 = self.gen_dummy_version_point(component_count)
            v1 = package.parse_version(self.fake_package_json_path, str(v0), self.fake_context_desc)
            self.assertEqual(v0, v1)

    #
    # Requirement, requirement list:
    #

    def test_requirement_list(self):
        vp0 = package.Version(0, 0, 0)
        vp1 = package.Version(1, 0, 0)
        req_list = package.parse_requirements_list(
            self.fake_package_json_path,
            [
                {
                    "provider": "git",
                    "location": self.fake_git_requirement_location,
                    "version": str(vp0)
                },
                {
                    "provider": "filesystem",
                    "location": self.fake_filesystem_requirement_location,
                    "version": str(vp1)
                }
            ]
        )
        
        self.assertEqual(len(req_list), 2)
        req0, req1 = req_list
        
        self.assertIsInstance(req0, package.GitRequirement)
        self.assertEqual(req0.provider, "git")
        self.assertEqual(req0.location, self.fake_git_requirement_location)
        self.assertEqual(len(req0.version_constraints), 1)
        self.assertEqual(req0.version_constraints[0], package.ExactVersionConstraint(vp0))
        
        self.assertIsInstance(req1, package.FilesystemRequirement)
        self.assertEqual(req1.provider, "filesystem")
        self.assertEqual(req1.location, self.fake_filesystem_requirement_location)
        self.assertEqual(len(req1.version_constraints), 1)
        self.assertEqual(req1.version_constraints[0], package.ExactVersionConstraint(vp1))

    def test_requirement_with_provider_filesystem__explicit_version(self):
        vp = package.Version(1, 0, 0)
        requirement_json = {
            "provider": "filesystem",
            "location": self.fake_filesystem_requirement_location,
            "version": str(vp)
        }
        requirement = package.parse_requirement(
            self.fake_package_json_path,
            requirement_json,
            self.fake_requirement_desc
        )
        self.assertIsInstance(requirement, package.FilesystemRequirement)
        self.assertEqual(requirement.provider, "filesystem")
        self.assertEqual(len(requirement.version_constraints), 1)
        self.assertEqual(requirement.version_constraints[0], package.ExactVersionConstraint(vp))
        self.assertEqual(requirement.location, self.fake_filesystem_requirement_location)

    def test_requirement_with_provider_filesystem__implicit_version(self):
        requirement_json = {
            "provider": "filesystem",
            "location": self.fake_filesystem_requirement_location
        }
        requirement = package.parse_requirement(
            self.fake_package_json_path,
            requirement_json,
            self.fake_requirement_desc
        )
        self.assertIsInstance(requirement, package.FilesystemRequirement)
        self.assertEqual(requirement.provider, "filesystem")
        self.assertEqual(requirement.version_constraints, [])
        self.assertEqual(requirement.location, self.fake_filesystem_requirement_location)

    def test_requirement_with_provider_git__explicit_version(self):
        vp = package.Version(1, 0, 0)
        requirement_json = {
            "provider": "git",
            "location": self.fake_git_requirement_location,
            "version": str(vp)
        }
        requirement = package.parse_requirement(
            self.fake_package_json_path,
            requirement_json,
            self.fake_requirement_desc
        )
        self.assertIsInstance(requirement, package.GitRequirement)
        self.assertEqual(requirement.provider, "git")
        self.assertEqual(len(requirement.version_constraints), 1)
        self.assertEqual(requirement.version_constraints[0], package.ExactVersionConstraint(vp))
        self.assertEqual(requirement.location, self.fake_git_requirement_location)

    def test_requirement_with_provider_git__implicit_version(self):
        requirement_json = {
            "provider": "git",
            "location": self.fake_git_requirement_location
        }
        requirement = package.parse_requirement(
            self.fake_package_json_path,
            requirement_json,
            self.fake_requirement_desc
        )
        self.assertIsInstance(requirement, package.GitRequirement)
        self.assertEqual(requirement.provider, "git")
        self.assertEqual(requirement.version_constraints, [])
        self.assertEqual(requirement.location, self.fake_git_requirement_location)
    
    #
    # Requirement version constraints: e.g. '*', '1.2.3.4', '[">=1.2.3", ...]'
    # raw_version_obj is either...
    # - a string denoting a version number (exact constraint specifier)
    # - a list of >=, >, <=, < version constraints
    # - the wild-card version specifier, '*'
    #

    def test_requirement_version_constraints__exact_version(self):
        component_count_iterator = range(
            package.Version.min_component_count, 
            package.Version.max_component_count + 1
        )
        for component_count in component_count_iterator:
            version_point = self.gen_dummy_version_point(component_count)
            constraints = package.parse_requirement_version_constraints(
                self.fake_package_json_path,
                str(version_point),
                self.fake_requirement_desc
            )
            self.assertEqual(len(constraints), 1)
            self.assertIsInstance(constraints[0], package.ExactVersionConstraint)
            self.assertEqual(constraints[0].point, version_point)

    def test_requirement_version_constraints__wildcard(self):
        wildcard_version_specifier = "*"
        constraints = package.parse_requirement_version_constraints(
            self.fake_package_json_path,
            wildcard_version_specifier,
            self.fake_requirement_desc
        )
        self.assertEqual(len(constraints), 0)

    def test_requirement_version_constraints__list_of_string_constraints(self):
        for constraint_count in [0, 1, 5]:
            rel_operators_map = {
                "<": (package.MaxVersionConstraint, False),
                ">": (package.MinVersionConstraint, False),
                "<=": (package.MaxVersionConstraint, True),
                ">=": (package.MinVersionConstraint, True)
            }
            rel_operators_domain = list(rel_operators_map.keys())
            rel_operators_list = [
                random.choice(rel_operators_domain) 
                for _ in range(constraint_count)
            ]
            version_point_list = [
                self.gen_dummy_version_point() 
                for _ in range(constraint_count)
            ]
            string_constraints_list = [
                rel_operator_str + str(version_point)
                for rel_operator_str, version_point in zip(rel_operators_list, version_point_list)
            ]
            
            c_list = package.parse_requirement_version_constraints(
                self.fake_package_json_path,
                string_constraints_list,
                self.fake_requirement_desc
            )

            assert len(rel_operators_list) == constraint_count
            assert len(version_point_list) == constraint_count
            self.assertEqual(len(c_list), constraint_count)

            for rel_operator, constraint in zip(rel_operators_list, c_list):
                constraint_type, is_closed = rel_operators_map[rel_operator]
                self.assertIsInstance(constraint, constraint_type)
                self.assertEqual(constraint.closed, is_closed)

            for version_point, constraint in zip(version_point_list, c_list):
                self.assertEqual(constraint.point, version_point)

    #
    # Single requirement version constraints: e.g. >=0.0.0, =1.0.0, <3.14.5
    #

    def test_parse_relative_requirement_version_constraint_string(self):
        component_count_iterator = range(
            package.Version.min_component_count, 
            package.Version.max_component_count + 1
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
    def gen_dummy_version_point(component_count=None):
        if component_count is None:
            component_count = random.randint(
                package.Version.min_component_count,
                package.Version.max_component_count
            )

        return package.Version.from_components([
            random.randint(0, (1<<8)-1)
            for _ in range(component_count)
        ])


if __name__ == '__main__':
    unittest.main()
    
