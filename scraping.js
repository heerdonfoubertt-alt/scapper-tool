const fs = require("fs");
const axios = require("axios");
const cheerio = require("cheerio");
const csv = require("csv-parser");
const { createObjectCsvWriter } = require("csv-writer");

const INPUT_CSV = "streamers_moins_1M_followers.csv";
const OUTPUT_CSV = "streamers_avec_twitch.csv";

const streamers = [];

fs.createReadStream(INPUT_CSV)
  .pipe(csv())
  .on("data", (row) => {
    // Construire l'URL profil
    row.profile_url = `https://streameurs.fr/streamer/${encodeURIComponent(row.Nom)}`;
    streamers.push(row);
  })
  .on("end", async () => {
    console.log(`📥 ${streamers.length} streamers à traiter`);

    for (let i = 0; i < streamers.length; i++) {
      const streamer = streamers[i];

      try {
        const { data } = await axios.get(streamer.profile_url, {
          timeout: 10000,
          headers: { "User-Agent": "Mozilla/5.0" }
        });

        const $ = cheerio.load(data);
        const twitchLink = $('a[href*="twitch.tv"]').attr("href") || "";
        streamer.twitch_url = twitchLink;

        console.log(`✔ ${streamer.Nom} → ${twitchLink || "❌"}`);

      } catch (err) {
        streamer.twitch_url = "";
        console.log(`⚠️ ${streamer.Nom} → erreur`);
      }

      await new Promise(r => setTimeout(r, 500)); // pause 0.5s
    }

    const csvWriter = createObjectCsvWriter({
      path: OUTPUT_CSV,
      header: Object.keys(streamers[0]).map(key => ({
        id: key,
        title: key
      }))
    });

    await csvWriter.writeRecords(streamers);
    console.log(`✅ Fichier créé : ${OUTPUT_CSV}`);
  });
