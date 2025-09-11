# Deployment Guide: AWS App Runner (Recommended Strategy)

This guide details how to deploy the application using **AWS App Runner**, a fully managed service that is more modern, cost-effective, and scalable than a traditional EC2 instance for this use case.

**Key Advantages:**

- **Cost-Effective:** App Runner can scale down to zero, so you only pay for compute when the application is actively being used.
- **Fully Managed:** AWS handles the server infrastructure, load balancing, security, and scaling.
- **Simple Deployments:** Deploys directly from your source code repository.

---

### Prerequisites

1. **Boto3 Refactoring:** The application code has been updated to use the `boto3` library instead of relying on the `aws-cli`.
2. **Dockerfile:** The project root contains a `Dockerfile`, which provides instructions for App Runner to build the application container.
3. **Source Code Repository:** Your code must be pushed to a GitHub (or Bitbucket) repository.

---

### Step 1: Create an IAM Role for App Runner

App Runner needs permissions to call AWS services (EC2, CloudWatch) on your behalf.

1. Navigate to **IAM** in the AWS Console.
2. Create a new **Role**.
3. For **Trusted entity type**, select **"AWS service"**.
4. For **Use case**, find and select **"App Runner"**. In the dropdown below, choose **"App Runner EC2 access"**. This creates the correct trust policy.
5. Click **Next**.
6. On the **Add permissions** page, search for and add the following AWS managed policies:
   * `CloudWatchReadOnlyAccess`
   * `AmazonEC2ReadOnlyAccess`
7. Click **Next**.
8. **Name the role:** Use a descriptive name, such as `AppRunnerServiceRole`, and finish creating the role.

---

### Step 2: Create and Configure the App Runner Service

1. Navigate to **AWS App Runner** in the console.
2. Click **"Create service"**.
3. **Source and deployment:**
   * **Source:** Choose **"Source code repository"**.
   * **Connection:** If this is your first time, create a new connection to your GitHub account. Authorize AWS to access your repositories.
   * **Repository:** Choose your project's repository and the branch to deploy (e.g., `main`).
   * **Deployment trigger:** Select **"Automatic"** to have every push to the branch trigger a new deployment.
4. Click **Next**.
5. **Configure build:**
   * On this page, select the option **"Configure all settings here"**.
   * App Runner will **automatically detect** the `Dockerfile` in your repository. You do not need to select a "Runtime" from the dropdown menu.
   * The only setting you must confirm on this screen is the port.
   * **Port:** Enter `8501`.
6. Click **Next**.
7. **Configure service:**
   * **Service name:** Choose a name for your service, like `dashboard-epmaps-beta`.
   * **Security - Instance role:** In this section, find and select the IAM role you created in Step 1 (`AppRunnerServiceRole`).
8. Click **Next**.
9. **Review and create:** Review the configuration and click **"Create & deploy"**.

---

### Step 3: Access Your Application

1. **Wait for Deployment:** The first deployment will take several minutes. App Runner is building the container image from your `Dockerfile` and deploying it. You can view the progress in the deployment logs.
2. **Access the URL:** Once the service status changes to **"Running"**, App Runner will provide a **"Default domain"**. This is the public URL for your application.

   `https://<unique_id>.awsapprunner.com`

Anyone with this URL can now access the beta version of your application. The URL is already secured with HTTPS.
