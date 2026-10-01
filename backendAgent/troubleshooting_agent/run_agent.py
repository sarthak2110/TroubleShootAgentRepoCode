from agent import support_agent
from config import setup_logger

logger = setup_logger("runner")

SAMPLE_ADMIN_DATA = """
KB-ALM-001
403 PERMISSION_DENIED: Caller does not have required IAM permissions
The service account executing the lifecycle pipeline lacks roles (e.g., roles/applifecyclemanager.admin or deployment service account impersonation).
Initialization / Provisioning
1. Identify the caller service agent or user account from Cloud Audit Logs.
2. Grant roles/applifecyclemanager.admin or the target resource editor role.
3. If workload identity federation or cross-project deployment is used, ensure roles/iam.serviceAccountTokenCreator is bound to the deployer principal.
"""

USER_QUERY = "I am getting a 403 PERMISSION_DENIED error during the lifecycle provisioning phase. How do I fix it?"


def main():
    logger.info("=== TEST 1: Admin Ingestion Service ===")
    admin_prompt = f"Please add this new data into the knowledge base:\n{SAMPLE_ADMIN_DATA}"
    admin_response = support_agent.run(admin_prompt)
    print("\n--- Agent Ingestion Response ---\n")
    print(admin_response.text)

    logger.info("=== TEST 2: User Retrieval Service ===")
    user_response = support_agent.run(USER_QUERY)
    print("\n--- Agent Retrieval Response ---\n")
    print(user_response.text)


if __name__ == "__main__":
    main()