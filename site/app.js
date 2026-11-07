(async function loadSightings() {
  const status = document.getElementById("status");
  const freshness = document.getElementById("freshness");
  const sightings = document.getElementById("sightings");
  const endpoint = window.BIRDALERT_API_ENDPOINT;

  if (typeof endpoint !== "string" || endpoint.length === 0) {
    status.textContent = "Sightings are unavailable right now.";
    status.classList.add("error");
    freshness.textContent = "Data freshness is unavailable right now.";
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

    const formatter = new Intl.DateTimeFormat("en-GB", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "Europe/London",
    });
    if (typeof payload.last_successful_processing_at === "string") {
      freshness.textContent = `Data last processed: ${formatter.format(
        new Date(payload.last_successful_processing_at),
      )}`;
    } else {
      freshness.textContent = "Data freshness is not available yet.";
    }

    if (payload.sightings.length === 0) {
      status.textContent = "No recent sightings are available.";
      return;
    }

    for (const sighting of payload.sightings) {
      const row = document.createElement("tr");
      const commonName = document.createElement("strong");
      const location = document.createElement("span");
      const observedAt = document.createElement("time");
      const validation = document.createElement("span");

      commonName.className = "species-name";
      commonName.textContent = sighting.species.common_name;
      location.textContent = sighting.location.name;
      observedAt.className = "observed-time";
      observedAt.dateTime = sighting.observed_at;
      observedAt.textContent = formatter.format(new Date(sighting.observed_at));

      const isProvisional = sighting.validation_status === "provisional";
      validation.className = `validation-badge ${
        isProvisional ? "provisional" : "validated"
      }`;
      validation.textContent = isProvisional ? "Provisional" : "Validated";

      const speciesCell = document.createElement("td");
      speciesCell.dataset.label = "Species";
      speciesCell.append(commonName);
      const locationCell = document.createElement("td");
      locationCell.dataset.label = "Location";
      locationCell.append(location);
      const observedAtCell = document.createElement("td");
      observedAtCell.dataset.label = "Observed";
      observedAtCell.append(observedAt);
      const validationCell = document.createElement("td");
      validationCell.dataset.label = "Status";
      validationCell.append(validation);
      row.append(speciesCell, locationCell, observedAtCell, validationCell);
      sightings.append(row);
    }

    status.textContent = `${payload.sightings.length} latest sighting${
      payload.sightings.length === 1 ? "" : "s"
    }`;
  } catch (error) {
    console.error("Unable to load BirdAlert sightings", error);
    status.textContent = "Sightings are unavailable right now.";
    status.classList.add("error");
    freshness.textContent = "Data freshness is unavailable right now.";
  }
})();
