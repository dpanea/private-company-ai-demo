// Cloudflare Web Analytics with opt-out support.
// Visit with ?analytics=off to opt out (stored in localStorage); ?analytics=on to re-enable.
//
// The token below belongs to demo.danielpanea.com. Cloudflare Web Analytics tokens are
// public identifiers (they ship in every page), not secrets — but if you fork this repo
// and deploy your own demo, replace the token with your own so pageviews land in your
// dashboard instead of mine. Either edit the fallback string below or set
// window.CF_WEB_ANALYTICS_TOKEN in your HTML before this script runs.
(() => {
    const optOutKey = 'dpAnalyticsOptOut';
    const params = new URLSearchParams(window.location.search);

    if (params.get('analytics') === 'off') {
        localStorage.setItem(optOutKey, 'true');
    }

    if (params.get('analytics') === 'on') {
        localStorage.removeItem(optOutKey);
    }

    const analyticsDisabled = localStorage.getItem(optOutKey) === 'true';
    const token = window.CF_WEB_ANALYTICS_TOKEN || 'd916e3c92c804195a7b708753362ed59';
    const hasToken = /^[a-f0-9]{32}$/i.test(token);

    if (!analyticsDisabled && hasToken) {
        const script = document.createElement('script');
        script.defer = true;
        script.src = 'https://static.cloudflareinsights.com/beacon.min.js';
        script.dataset.cfBeacon = JSON.stringify({ token });
        document.head.appendChild(script);
    }
})();
