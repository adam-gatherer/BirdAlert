(async function loadSightings() {
  const status = document.getElementById("status");
  const sightings = document.getElementById("sightings");
  const endpoint = window.BIRDALERT_API_ENDPOINT;

  if (typeof endpoint !== "string" || endpoint.length === 0) {
    status.textContent = "Sightings are unavailable right now.";
    status.classList.add("error");
    return;
  }

  try {
    const response = await fetch(`${endpoint}/sightings`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Sightings request failed with status ${response.status}`);
    }

    const payload = await response.json();
    if (!Array.isArray(payload.sightings)) {
      throw new Error("Sightings response has an unexpected shape");
    }

    if (payload.sightings.length === 0) {
      status.textContent = "No recent sightings are available.";
      return;
    }

    const formatter = new Intl.DateTimeFormat("en-GB", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "Europe/London",
    });
    for (const sighting of payload.sightings) {
      const row = document.createElement("tr");
      const commonName = document.createElement("strong");
      const location = document.createElement("span");
      const observedAt = document.createElement("time");

      commonName.textContent = sighting.species.common_name;
      location.textContent = sighting.location.name;
      observedAt.dateTime = sighting.observed_at;
      observedAt.textContent = formatter.format(new Date(sighting.observed_at));

      const speciesCell = document.createElement("td");
      speciesCell.append(commonName);
      if (sighting.validation_status === "provisional") {
        const provisional = document.createElement("span");
        provisional.className = "provisional";
        provisional.textContent = " (provisional)";
        speciesCell.append(provisional);
      }
      const locationCell = document.createElement("td");
      locationCell.append(location);
      const observedAtCell = document.createElement("td");
      observedAtCell.append(observedAt);
      row.append(speciesCell, locationCell, observedAtCell);
      sightings.append(row);
    }

    status.textContent = `${payload.sightings.length} latest sightings`;
  } catch (error) {
    console.error("Unable to load BirdAlert sightings", error);
    status.textContent = "Sightings are unavailable right now.";
    status.classList.add("error");
  }
})();
