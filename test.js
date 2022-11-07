$.get(url, function (status, data) {
  const planningPermissions = data.planning_permissions;
  const nearestPostcodes = data.nearest_postcodes;
  const crimeStats = data.crimeStats;

  data = ["1", "2", "3"];

  for (item of planningPermissions) {
    const html = `
            <div class='planning-permission-wrapper'>
                <p>${item.description}</p>
                <p>${item.address}</p>
            </div>
        `;

    $("#");
  }
});
