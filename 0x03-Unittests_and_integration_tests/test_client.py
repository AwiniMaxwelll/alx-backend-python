#!/usr/bin/env python3
""" Test suite for client.py """
import unittest
from unittest.mock import patch, PropertyMock, Mock
from parameterized import parameterized, parameterized_class
from client import GithubOrgClient
from fixtures import TEST_PAYLOAD


class TestGithubOrgClient(unittest.TestCase):
    """Test Github.Org Client"""

    @parameterized.expand([
        ("google",),
        ("abc",),
    ])
    @patch('client.get_json')
    def test_org(self, org_name, mock_get_json):
        """Test that GithubOrgClient.org returns the correct value."""
        client = GithubOrgClient(org_name)
        client.org()
        mock_get_json.assert_called_once_with(
            f"https://api.github.com/orgs/{org_name}"
        )

    def test_public_repos_url(self):
        """Test that the result of _public_repos_url is correct."""
        with patch(
                'client.GithubOrgClient.org',
                new_callable=PropertyMock) as mock_org:
            payload = {"repos_url": "https://api.github.com/orgs/google/repos"}
            mock_org.return_value = payload
            client = GithubOrgClient("google")
            self.assertEqual(client._public_repos_url, payload["repos_url"])

    @patch('client.get_json')
    def test_public_repos(self, mock_get_json):
        """Test that public_repos returns the correct list of repos."""
        json_payload = [{"name": "repo1"}, {"name": "repo2"}]
        mock_get_json.return_value = json_payload

        with patch(
                'client.GithubOrgClient._public_repos_url',
                new_callable=PropertyMock) as mock_public_repos_url:
            url = "https://api.github.com/orgs/google/repos"
            mock_public_repos_url.return_value = f"{url}"
            client = GithubOrgClient("google")
            repos = client.public_repos()
            self.assertEqual(repos, ["repo1", "repo2"])
            mock_public_repos_url.assert_called_once()
            mock_get_json.assert_called_once()

    @parameterized.expand([
        ({"license": {"key": "my_license"}}, "my_license", True),
        ({"license": {"key": "other_license"}}, "my_license", False),
    ])
    def test_has_license(self, repo, license_key, expected):
        """Test the has_license static method."""
        self.assertEqual(
            GithubOrgClient.has_license(repo, license_key),
            expected
        )


@parameterized_class(
    ("org_payload", "repos_payload", "expected_repos", "apache2_repos"),
    TEST_PAYLOAD
)
class TestIntegrationGithubOrgClient(unittest.TestCase):
    """Integration tests for the GithubOrgClient class."""

    @classmethod
    def setUpClass(cls):
        """Set up for integration tests."""
        cls.get_patcher = patch('requests.get')
        mock_get = cls.get_patcher.start()

        def side_effect(url):
            """Side effect for mock requests.get."""
            mock_response = Mock()
            if url == cls.org_payload["repos_url"]:
                mock_response.json.return_value = cls.repos_payload
            else:
                mock_response.json.return_value = cls.org_payload
            return mock_response

        mock_get.side_effect = side_effect

    @classmethod
    def tearDownClass(cls):
        """Tear down for integration tests."""
        cls.get_patcher.stop()

    def test_public_repos(self):
        """Test public_repos method with integration setup."""
        client = GithubOrgClient("google")
        self.assertEqual(client.public_repos(), self.expected_repos)

    def test_public_repos_with_license(self):
        """Test public_repos method with license filter."""
        client = GithubOrgClient("google")
        self.assertEqual(
            client.public_repos(license="apache-2.0"), self.apache2_repos
        )
