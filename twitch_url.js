const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const { createObjectCsvWriter } = require('csv-writer');

const INPUT_CSV = 'streamers_moins_1M_followers.csv'; // ton CSV existant
const OUTPUT_CSV = 'streamers_avec_twitch.csv';

const streamers = [];

// Lire le CSV
fs.createReadStream(INPUT_CSV)
  .pipe(csv())
  .on('data', (row) => {
    // Construire le lien Twitch directement depuis le pseudo
    const twitch_url = `https://www.twitch.tv/${row.Nom}`;
    row.twitch_url = twitch_url;
    streamers.push(row);
  })
  .on('end', async () => {
    console.log(`📥 ${streamers.length} streamers traités`);

    // Écrire le nouveau CSV
    const csvWriter = createObjectCsvWriter({
      path: OUTPUT_CSV,
      header: Object.keys(streamers[0]).map(key => ({ id: key, title: key }))
    });

    await csvWriter.writeRecords(streamers);
    console.log(`✅ Fichier créé : ${OUTPUT_CSV}`);
  });
