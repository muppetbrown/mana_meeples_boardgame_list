// frontend/src/constants/aftergame.js
/**
 * AfterGame Integration Constants
 *
 * URLs and helper functions for integrating with AfterGame platform
 * to enable game session planning from the board game library.
 */

/**
 * AfterGame URLs for Mana & Meeples group
 */
export const AFTERGAME_URLS = {
  // Main group page
  GROUP: 'https://aftergame.app/groups/mana---meeples-9373',

  // View upcoming events
  UPCOMING_EVENTS: 'https://aftergame.app/groups/mana---meeples-9373/events?initialPast=false',

  // Base URL for creating new game events
  CREATE_GAME_BASE: 'https://aftergame.app/events/create?type=SPECIFIC_GAME&placeId=8f340e1e-05dd-4d98-86a4-4b4a47512d40&initialGroupId=9b196948-f86f-4600-b8be-cfea3768c9e5&initialGroupName=Mana%20%26%20Meeples%20Timaru'
};

/**
 * Generate AfterGame URL for planning a game session
 *
 * @param {string|null} aftergameGameId - AfterGame UUID for the specific game
 * @returns {string} URL to create game session on AfterGame
 *
 * @example
 * // With specific game ID
 * getAfterGameCreateUrl('ac3a5f77-3e19-47af-a61a-d648d04b02e2')
 * // Returns: https://aftergame.app/events/create?...&gameId=ac3a5f77-3e19-47af-a61a-d648d04b02e2
 *
 * // Without game ID (generic)
 * getAfterGameCreateUrl(null)
 * // Returns: https://aftergame.app/events/create?...
 */
export function getAfterGameCreateUrl(aftergameGameId) {
  if (!aftergameGameId) {
    return AFTERGAME_URLS.CREATE_GAME_BASE;
  }
  return `${AFTERGAME_URLS.CREATE_GAME_BASE}&gameId=${aftergameGameId}`;
}
