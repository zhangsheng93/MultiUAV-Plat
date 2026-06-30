#!/usr/bin/env python3
"""
Agent API Client for UAV Control Agent

Provides a wrapper for communicating with the UAV Agent Server (port 18000).
Handles async job submission, status polling, and result retrieval.

Author: UAV Control System
"""

import requests
import time
import logging
from typing import Optional, Dict, Any, Tuple


class AgentClient:
    """Client for interacting with the UAV Agent API Server."""

    def __init__(self, base_url: str = "http://localhost:18000", logger: Optional[logging.Logger] = None):
        """
        Initialize the Agent API client.

        Args:
            base_url: The base URL of the agent server (default: http://localhost:18000)
            logger: Optional logger instance for logging operations
        """
        self.base_url = base_url.rstrip('/')
        self.logger = logger or logging.getLogger("AgentClient")
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'UAV-Agent-Checker/1.0'
        })

    @staticmethod
    def _preview(value: Any, limit: int = 500) -> str:
        text = " ".join(str(value).split())
        if len(text) > limit:
            return text[:limit].rstrip() + "..."
        return text

    def _log_job_status(self, job_id: str, job_info: Dict[str, Any], elapsed: float) -> None:
        """Log a compact status snapshot for debugging agent/checker failures."""
        status = job_info.get('status', 'unknown')
        error = job_info.get('error')
        result = job_info.get('result') or {}
        result_success = result.get('success') if isinstance(result, dict) else None
        output = result.get('output') if isinstance(result, dict) else None

        details = [
            f"Job {job_id} status={status}",
            f"elapsed={elapsed:.1f}s",
        ]
        if error:
            details.append(f"error={self._preview(error)}")
        if result_success is not None:
            details.append(f"result_success={result_success}")
        if output:
            details.append(f"output={self._preview(output)}")

        self.logger.info(", ".join(details))

    def check_health(self) -> bool:
        """
        Check if the agent server is available.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                self.logger.info("Agent server health check: OK")
                return True
            else:
                self.logger.warning(f"Agent server health check failed with status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Agent server health check failed: {e}")
            return False

    def submit_command_async(self, command: str) -> Optional[Dict[str, Any]]:
        """
        Submit a command to the agent for asynchronous execution.

        Args:
            command: The natural language command to execute

        Returns:
            Response dict with job_id and status, or None if failed
            Example: {"job_id": "uuid", "status": "queued", "message": "..."}
        """
        try:
            self.logger.info(f"Submitting async command: {command[:100]}...")
            response = self.session.post(
                f"{self.base_url}/agent/command/async",
                json={"command": command},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                job_id = result.get('job_id')
                self.logger.info(f"Command submitted successfully. Job ID: {job_id}")
                return result
            else:
                self.logger.error(f"Failed to submit command. Status: {response.status_code}, Response: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error submitting command: {e}")
            return None

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a submitted job.

        Args:
            job_id: The job ID returned from submit_command_async

        Returns:
            Job status dict or None if failed
            Example: {"job_id": "uuid", "status": "running"|"completed"|"failed", "result": {...}}
        """
        try:
            response = self.session.get(
                f"{self.base_url}/agent/jobs/{job_id}",
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(
                    "Failed to get job status. "
                    f"Job ID: {job_id}, Status: {response.status_code}, "
                    f"Response: {self._preview(response.text)}"
                )
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error getting job status for {job_id}: {type(e).__name__}: {e}")
            return None

    def wait_for_completion(
        self,
        job_id: str,
        poll_interval: float = 10.0,
        timeout: float = 500.0,
        status_callback: Optional[callable] = None,
        max_status_failures: int = 5
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Wait for a job to complete by polling its status.

        Args:
            job_id: The job ID to monitor
            poll_interval: Seconds between status checks (default: 10.0)
            timeout: Maximum time to wait in seconds (default: 500.0)
            status_callback: Optional callback function called with status updates
                            Signature: callback(status: str, elapsed_time: float) -> bool
                            Return False to cancel waiting
            max_status_failures: Consecutive status poll failures to tolerate before giving up

        Returns:
            Tuple of (success: bool, result: dict or None)
            - success: True if job completed successfully, False if failed or timeout
            - result: The complete job result dict if completed, None otherwise
        """
        start_time = time.time()
        consecutive_status_failures = 0

        self.logger.info(f"Waiting for job {job_id} to complete (timeout: {timeout}s)...")

        while True:
            elapsed = time.time() - start_time

            # Check timeout
            if elapsed > timeout:
                self.logger.error(f"Job {job_id} timed out after {elapsed:.1f}s")
                return False, None

            # Get job status
            job_info = self.get_job_status(job_id)
            if not job_info:
                consecutive_status_failures += 1
                self.logger.warning(
                    f"Failed to get status for job {job_id} "
                    f"({consecutive_status_failures}/{max_status_failures}); retrying..."
                )
                if consecutive_status_failures >= max_status_failures:
                    self.logger.error(
                        f"Failed to get status for job {job_id} after "
                        f"{consecutive_status_failures} consecutive attempts"
                    )
                    return False, None
                time.sleep(poll_interval)
                continue

            consecutive_status_failures = 0

            status = job_info.get('status', 'unknown')
            self._log_job_status(job_id, job_info, elapsed)

            # Call status callback if provided
            if status_callback:
                try:
                    should_continue = status_callback(status, elapsed)
                    if not should_continue:
                        self.logger.info(f"Job {job_id} monitoring cancelled by callback")
                        return False, None
                except Exception as e:
                    self.logger.error(f"Error in status callback: {e}")

            # Check if job is complete
            if status == 'completed':
                result = job_info.get('result', {})
                success = result.get('success', False)
                self.logger.info(f"Job {job_id} completed successfully. Success: {success}")
                return True, job_info

            elif status == 'failed':
                error = job_info.get('error', 'Unknown error')
                self.logger.error(f"Job {job_id} failed: {error}")
                return False, job_info

            # Still running or queued, wait before next poll
            self.logger.debug(f"Job {job_id} status: {status}, elapsed: {elapsed:.1f}s")
            time.sleep(poll_interval)

    def submit_and_wait(
        self,
        command: str,
        poll_interval: float = 10.0,
        timeout: float = 500.0,
        status_callback: Optional[callable] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Convenience method: Submit a command and wait for completion.

        Args:
            command: The natural language command to execute
            poll_interval: Seconds between status checks (default: 10.0)
            timeout: Maximum time to wait in seconds (default: 500.0)
            status_callback: Optional callback for status updates

        Returns:
            Tuple of (success: bool, result: dict or None)
        """
        # Submit command
        submission = self.submit_command_async(command)
        if not submission:
            self.logger.error("Failed to submit command")
            return False, None

        job_id = submission.get('job_id')
        if not job_id:
            self.logger.error("No job_id in submission response")
            return False, None

        # Wait for completion
        return self.wait_for_completion(job_id, poll_interval, timeout, status_callback)

    def get_session_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get the current agent session summary.

        Returns:
            Session summary dict or None if failed
        """
        try:
            response = self.session.get(f"{self.base_url}/agent/session", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get session summary. Status: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error getting session summary: {e}")
            return None
