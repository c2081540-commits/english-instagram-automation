/**
 * Clock-only dispatcher. Store all values in Script Properties.
 * It never reads queue data and never calls Meta APIs.
 */
function dispatchDuePostChecks() {
  const properties = PropertiesService.getScriptProperties();
  const token = requireProperty_(properties, 'GITHUB_DISPATCH_TOKEN');
  const owner = requireProperty_(properties, 'GITHUB_OWNER');
  const repositories = [
    requireProperty_(properties, 'INSTAGRAM_REPOSITORY'),
    requireProperty_(properties, 'THREADS_REPOSITORY'),
  ];

  repositories.forEach(function(repository) {
    const response = UrlFetchApp.fetch(
      'https://api.github.com/repos/' + encodeURIComponent(owner) + '/' +
        encodeURIComponent(repository) + '/dispatches',
      {
        method: 'post',
        contentType: 'application/json',
        headers: {
          Authorization: 'Bearer ' + token,
          Accept: 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28',
        },
        payload: JSON.stringify({
          event_type: 'due-post-check',
          client_payload: {source: 'gas-clock'},
        }),
        muteHttpExceptions: true,
      }
    );
    if (response.getResponseCode() !== 204) {
      throw new Error('GitHub dispatch failed for ' + repository +
                      ' with HTTP ' + response.getResponseCode());
    }
  });
}

function installFiveMinuteTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(function(trigger) {
      return trigger.getHandlerFunction() === 'dispatchDuePostChecks';
    })
    .forEach(function(trigger) {
      ScriptApp.deleteTrigger(trigger);
    });

  ScriptApp.newTrigger('dispatchDuePostChecks')
    .timeBased()
    .everyMinutes(5)
    .create();
}

function requireProperty_(properties, name) {
  const value = properties.getProperty(name);
  if (!value) {
    throw new Error('Missing Script Property: ' + name);
  }
  return value;
}

