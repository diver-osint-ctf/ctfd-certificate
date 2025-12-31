document.addEventListener("DOMContentLoaded", () => {
  // Only run on team pages
  if (!location.pathname.startsWith("/team")) {
    return;
  }

  const captainMenu = document.querySelector('div[x-data="CaptainMenu"]');
  const teamHeader = document.querySelector("h1#team-id");

  // Target container: CaptainMenu (preferred) or append after Team Header
  let targetContainer = captainMenu;

  if (!targetContainer && teamHeader) {
    // Fallback: Create a container if CaptainMenu doesn't exist
    const container = document.createElement("div");
    container.style.marginTop = "10px";
    teamHeader.parentElement.appendChild(container);
    targetContainer = container;
  }

  if (targetContainer) {
    // Check if CTF has ended
    const currentTime = Math.floor(Date.now() / 1000); // Unix timestamp in seconds
    const ctfEndTime = window.init.end;

    // If CTF hasn't ended, don't show the button at all
    if (!ctfEndTime || currentTime < ctfEndTime) {
      return;
    }

    // Get team ID from URL or window.init
    const teamId = window.init.teamId || location.pathname.split("/").pop();

    // Fetch team information to check rank
    fetch(`/api/v1/teams/${teamId}`, {
      credentials: "same-origin",
    })
      .then((response) => response.json())
      .then((teamData) => {
        const team = teamData.data;
        const rank = team.place || 0;

        const btnLink = document.createElement("a");
        btnLink.className =
          "generate-certificate text-white certificate-tooltip";
        btnLink.id = "generate-certificate-link";

        const icon = document.createElement("i");
        icon.className = "cursor-pointer fas fa-certificate fa-2x px-2 pt-3";

        // Create custom tooltip that matches Bootstrap's style exactly
        const tooltipText = document.createElement("span");
        tooltipText.className = "tooltip-inner";

        // Check if rank is 0 or null
        if (rank === 0 || rank === null) {
          // Disable button
          btnLink.style.cursor = "not-allowed";
          btnLink.style.opacity = "0.5";
          icon.className = "fas fa-certificate fa-2x px-2 pt-3";
          tooltipText.textContent = "No rank yet";

          // Prevent click event
          btnLink.addEventListener("click", function (e) {
            e.preventDefault();
          });
        } else {
          // Enable button
          btnLink.style.cursor = "pointer";
          tooltipText.textContent = "Generate Certificate";

          btnLink.addEventListener("click", function (e) {
            e.preventDefault();

            // UI Feedback
            this.style.pointerEvents = "none";
            icon.className = "fas fa-spinner fa-spin fa-2x px-2 pt-3";

            const formData = new FormData();
            formData.append("nonce", window.init.csrfNonce);

            fetch("/certificates/generate", {
              method: "POST",
              body: formData,
              credentials: "same-origin",
            })
              .then((response) => response.json())
              .then((data) => {
                if (data.success) {
                  window.open(data.view_url, "_blank");
                } else {
                  alert(
                    "Error: " + (data.error || "Failed to generate certificate")
                  );
                }
              })
              .catch((error) => {
                console.error("Error:", error);
                alert("Failed to generate certificate");
              })
              .finally(() => {
                // Reset UI
                this.style.pointerEvents = "auto";
                icon.className =
                  "cursor-pointer fas fa-certificate fa-2x px-2 pt-3";
              });
          });
        }

        btnLink.appendChild(icon);
        btnLink.appendChild(tooltipText);
        targetContainer.appendChild(btnLink);
      })
      .catch((error) => {
        console.error("Failed to fetch team info:", error);
        // Still show button even if API fails, but disabled
        const btnLink = document.createElement("a");
        btnLink.className =
          "generate-certificate text-white certificate-tooltip";
        btnLink.id = "generate-certificate-link";
        btnLink.style.cursor = "not-allowed";
        btnLink.style.opacity = "0.5";

        const icon = document.createElement("i");
        icon.className = "fas fa-certificate fa-2x px-2 pt-3";

        const tooltipText = document.createElement("span");
        tooltipText.className = "tooltip-inner";
        tooltipText.textContent = "Unable to verify rank";

        btnLink.appendChild(icon);
        btnLink.appendChild(tooltipText);
        targetContainer.appendChild(btnLink);

        btnLink.addEventListener("click", function (e) {
          e.preventDefault();
        });
      });
  }
});
