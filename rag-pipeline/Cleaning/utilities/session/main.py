import boto3
from utilities.settings.settings import settings
from botocore.config import Config


class Boto3Session:
    """
    A class to manage and reuse a Boto3 session across an application. This class provides
    methods to get Boto3 clients and resources for interacting with AWS services.

    Attributes:
    - _session : boto3.Session
        A private class-level attribute that stores a single instance of the Boto3 session.

    Methods:
    - get_session(): Returns a Boto3 session object, creating it if it doesn't already exist.
    - get_client(service_name, region_name=os.getenv("AWS_REGION")): Returns a Boto3 client for a specified AWS service.
    - get_resource(service_name, region_name=os.getenv("AWS_REGION")): Returns a Boto3 resource for a specified AWS service.
    """

    _session = None

    @classmethod
    def get_session(cls, region_name=settings.AWS_REGION):
        """
        Retrieves the Boto3 session. If the session does not already exist, it creates a new one
        using the AWS profile name specified in the environment variable 'PROFILE_NAME'.

        Returns:
        - boto3.Session: The Boto3 session object.
        """
        if cls._session is None:
            cls._session = boto3.Session(region_name=region_name)
        return cls._session

    @classmethod
    def get_client(
        cls,
        service_name,
        region_name=settings.AWS_REGION,
    ):
        """
        Returns a Boto3 client for a specified AWS service. The client is created using the session managed by the `get_session` method.

        Parameters:
        - service_name (str): The name of the AWS service for which the client is requested (e.g., 's3', 'ec2').
        - region_name (str, optional): The AWS region name (e.g., 'us-west-2'). If not provided, the region is taken from the environment variable 'AWS_REGION'.

        Returns:
        - boto3.client: A Boto3 client object for the specified service.
        """

        session = cls.get_session()
        return session.client(
            service_name, region_name=region_name, config=Config(read_timeout=1000)
        )

    @classmethod
    def get_resource(
        cls,
        service_name,
        region_name=settings.AWS_REGION,
    ):
        """
        Returns a Boto3 resource for a specified AWS service. The resource is created using the session managed by the `get_session` method.

        Parameters:
        - service_name (str): The name of the AWS service for which the resource is requested (e.g., 's3', 'dynamodb').
        - region_name (str, optional): The AWS region name (e.g., 'us-west-2'). If not provided, the region is taken from the environment variable 'AWS_REGION'.

        Returns:
        - boto3.resource: A Boto3 resource object for the specified service.
        """
        session = cls.get_session()
        return session.resource(service_name, region_name=region_name)


session = Boto3Session()