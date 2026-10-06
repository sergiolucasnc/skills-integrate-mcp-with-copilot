document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const signupContainer = document.getElementById("signup-container");
  const messageDiv = document.getElementById("message");
  const accountButton = document.getElementById("account-button");
  const accountMenu = document.getElementById("account-menu");
  const accountStatus = document.getElementById("account-status");
  const loginOpenButton = document.getElementById("login-open-button");
  const logoutButton = document.getElementById("logout-button");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginError = document.getElementById("login-error");
  let isTeacher = false;

  function updateTeacherControls(username) {
    isTeacher = Boolean(username);
    signupContainer.classList.toggle("hidden", !isTeacher);
    accountStatus.textContent = username ? `Signed in as ${username}` : "Not signed in";
    loginOpenButton.classList.toggle("hidden", isTeacher);
    logoutButton.classList.toggle("hidden", !isTeacher);
    fetchActivities();
  }

  function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");
    setTimeout(() => messageDiv.classList.add("hidden"), 5000);
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) {
        throw new Error("Unable to load activities");
      }
      const activities = await response.json();
      const selectedActivity = activitySelect.value;
      activitiesList.replaceChildren();
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) =>
                      `<li><span class="participant-email">${email}</span>${
                        isTeacher
                          ? `<button class="delete-btn" data-activity="${name}" data-email="${email}" aria-label="Unregister ${email}">❌</button>`
                          : ""
                      }</li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;
        activitiesList.appendChild(activityCard);

        const option = new Option(name, name);
        option.selected = name === selectedActivity;
        activitySelect.appendChild(option);
      });

      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.currentTarget;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        { method: "DELETE" }
      );
      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        fetchActivities();
      } else {
        if (response.status === 401) {
          updateTeacherControls(null);
        }
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("email").value;
    const activity = activitySelect.value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        { method: "POST" }
      );
      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();
        fetchActivities();
      } else {
        if (response.status === 401) {
          updateTeacherControls(null);
        }
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  accountButton.addEventListener("click", () => {
    const isOpen = !accountMenu.classList.contains("hidden");
    accountMenu.classList.toggle("hidden", isOpen);
    accountButton.setAttribute("aria-expanded", String(!isOpen));
  });

  loginOpenButton.addEventListener("click", () => {
    accountMenu.classList.add("hidden");
    accountButton.setAttribute("aria-expanded", "false");
    loginError.classList.add("hidden");
    loginForm.reset();
    loginDialog.showModal();
  });

  document.getElementById("login-cancel-button").addEventListener("click", () => {
    loginDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginError.classList.add("hidden");
    const formData = new FormData(loginForm);

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Unable to log in");
      }
      loginDialog.close();
      loginForm.reset();
      updateTeacherControls(result.username);
      showMessage("Teacher login successful", "success");
    } catch (error) {
      loginError.textContent = error.message || "Unable to log in";
      loginError.classList.remove("hidden");
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      if (!response.ok) {
        throw new Error("Unable to log out");
      }
      accountMenu.classList.add("hidden");
      accountButton.setAttribute("aria-expanded", "false");
      updateTeacherControls(null);
      showMessage("Logged out", "success");
    } catch (error) {
      showMessage(error.message || "Unable to log out", "error");
    }
  });

  fetch("/auth/status")
    .then(async (response) => {
      const status = await response.json();
      if (!response.ok) {
        throw new Error(status.detail || "Unable to check teacher login");
      }
      return status;
    })
    .then((status) => {
      updateTeacherControls(status.authenticated ? status.username : null);
    })
    .catch((error) => {
      console.error("Error checking teacher login:", error);
      updateTeacherControls(null);
      showMessage(
        `Could not check teacher login: ${error.message || "request failed"}`,
        "error"
      );
    });
});
