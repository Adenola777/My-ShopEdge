/**
 * The addresses that join the website and the app, in one place (the navigation the owner
 * approved on 11 October 2026). The website is a separate static site, so its links are
 * absolute; the app's own pages are paths.
 */

export const LANDING_URL = "https://myshopedge.inspirecraftglobal.com";

/** The website's sections and pages, as the app's top bar and More page link to them. */
export const SITE = {
  home: `${LANDING_URL}/`,
  features: `${LANDING_URL}/#features`,
  how: `${LANDING_URL}/#how`,
  explainer: `${LANDING_URL}/tools/tiktok-shop-payout-explainer`,
  faq: `${LANDING_URL}/faq/tiktok-shop-seller-finance`,
};

export const SIGN_IN = "/handler/sign-in";
export const SIGN_OUT = "/handler/sign-out";
export const START = "/start";
export const PRICING = "/pricing";
