const puppeteer = require('puppeteer');
const fs = require('fs');
const Papa = require('papaparse');

(async () => {
    // Lire le CSV
    const file = fs.readFileSync('streamers.csv', 'utf8');
    const data = Papa.parse(file, { header: true }).data;

    // Résultats
    const results = [];

    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();

    for (const streamer of data) {
        const url = streamer.twitch_url;
        console.log(`🔍 Analyse de ${streamer.pseudo}...`);

        try {
            await page.goto(url, { waitUntil: 'networkidle2' });

            // Attendre le selecteur bio
            await page.waitForSelector('[data-a-target="user-bio"]', { timeout: 5000 });

            const bio = await page.$eval('[data-a-target="user-bio"]', el => el.textContent.trim());

            // Chercher un email dans la bio
            const emailRegex = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i;
            const match = bio.match(emailRegex);

            results.push({
                pseudo: streamer.pseudo,
                twitch_url: url,
                bio: bio,
                email: match ? match[0] : ''
            });

            console.log(`✅ ${streamer.pseudo} analysé`);
        } catch (err) {
            console.log(`⚠️ Erreur ${streamer.pseudo}: ${err.message}`);
            results.push({
                pseudo: streamer.pseudo,
                twitch_url: url,
                bio: '',
                email: ''
            });
        }
    }

    await browser.close();

    // Écrire le CSV
    const csv = Papa.unparse(results);
    fs.writeFileSync('streamers_result.csv', csv, 'utf8');
    console.log('✅ Scraping terminé. Fichier créé : streamers_result.csv');
})();
