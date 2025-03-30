# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""
This test module contains tests that verify the Worker agent's behavior by submitting jobs to the
Deadline Cloud service and checking that the result/output of the jobs is as we expect it.
"""

import os
from typing import Optional
import backoff
import pytest
import logging
import time
from deadline_test_fixtures import (
    DeadlineClient,
    TaskStatus,
    EC2InstanceWorker,
)
from deadline_test_fixtures.deadline import WorkerLog
from e2e.utils import submit_sleep_job
import boto3
import botocore.client

LOG = logging.getLogger(__name__)


class TestHostConfiguration:
    @pytest.mark.skip
    @pytest.mark.skipif(
        os.environ["OPERATING_SYSTEM"] != "linux",
        reason="Linux specific test",
    )
    def test_linux_host_configuration(
        self,
        deadline_resources,
        session_worker: EC2InstanceWorker,
        deadline_client: DeadlineClient,
    ) -> None:
        # WHEN

        job = submit_sleep_job(
            "Test Success Sleep Job",
            deadline_client,
            deadline_resources.farm,
            deadline_resources.queue_a,
        )

        # THEN
        LOG.info(f"Waiting for job {job.id} to complete")
        job.wait_until_complete(client=deadline_client)
        LOG.info(f"Job result: {job}")

        assert job.task_run_status == TaskStatus.SUCCEEDED

        # The logs we are looking for are at the worker agent startup.
        # The logs should be available well before the job is completed.

        logs_client = boto3.client(
            "logs",
            config=botocore.config.Config(retries={"max_attempts": 10, "mode": "adaptive"}),
        )
        logs: WorkerLog = session_worker.get_logs(logs_client=logs_client)
        logs.assert_pattern_in_log(
            expected_pattern="Worker Agent host configuration succeeded. Starting worker session loop.",
            failure_msg="Cannot find Host Config logs.",
        )

    @pytest.mark.skipif(
        os.environ["OPERATING_SYSTEM"] != "linux",
        reason="Linux specific test",
    )
    def test_bad_linux_host_configuration(
        self,
        deadline_resources,
        session_worker: EC2InstanceWorker,
        deadline_client: DeadlineClient,
    ) -> None:
        # WHEN
        # Worker startsup, the host should exit and shutdown as soon as script fails.
        
        ec2_client = boto3.client("ec2")
        instance_id: Optional[str] = session_worker.instance_id
        assert instance_id

        @backoff.on_exception(
            backoff.constant,
            Exception,
            max_time=800,
            interval=30,
        )
        def check_instance_stopping() -> None:
            instance_status = ec2_client.describe_instance_status(
                InstanceIds=[instance_id], IncludeAllInstances=True
            )["InstanceStatuses"][0]["InstanceState"]

            assert instance_status["Name"] in ["stopped", "stopping"]

        check_instance_stopping()

    @pytest.mark.skipif(
        os.environ["OPERATING_SYSTEM"] != "windows",
        reason="Windows specific test",
    )
    def test_windows_host_configuration(
        self,
        deadline_resources,
        session_worker: EC2InstanceWorker,
        deadline_client: DeadlineClient,
    ) -> None:
        # Given

        # Make sure UAC is OFF, otherwise runAs will fail and wait forever to accept UAC.
        # cmd_result = session_worker.send_command(
        #    "REG ADD HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System /v ConsentPromptBehaviorAdmin /t REG_DWORD /d 0 /f",
        # )
        # assert cmd_result.exit_code == 0, "Failed to set UAC prompt OFF command on worker instance"
        # WHEN

        # The logs we are looking for are at the worker agent startup.
        # The logs should be available well before the job is completed.
        for i in range(3):
            LOG.info(f"Waiting to get logs")
            logs_client = boto3.client(
                "logs",
                config=botocore.config.Config(retries={"max_attempts": 10, "mode": "adaptive"}),
            )
            logs: WorkerLog = session_worker.get_logs(logs_client=logs_client)
            time.sleep(60)
        # logs.assert_pattern_in_log(expected_pattern="Worker Agent host configuration successful. Exit code 0. Starting worker session loop.", failure_msg="Cannot find Host Config logs.")


"""
        job = submit_sleep_job(
            "Test Success Sleep Job",
            deadline_client,
            deadline_resources.farm,
            deadline_resources.queue_a,
        )

        # THEN
        LOG.info(f"Waiting for job {job.id} to complete")
        job.wait_until_complete(client=deadline_client)
        LOG.info(f"Job result: {job}")

        assert job.task_run_status == TaskStatus.SUCCEEDED
"""
