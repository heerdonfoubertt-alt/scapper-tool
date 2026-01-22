const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({
        headless: true,
        executablePath: puppeteer.executablePath()
    });

    console.log("🎉 Chromium lancé avec succès !");
    await browser.close();
})();
