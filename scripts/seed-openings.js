// Seed script: Populates the categories database with chess opening data (ECO A-E)
// Run via: kubectl exec mongodb-pod -- mongosh -u lbtuser -p 'lbt-db-pass-2026' --authenticationDatabase admin mdr-categories /tmp/seed-openings.js

const db = db.getSiblingDB('mdr-categories');

// Check if already seeded
const existing = db.categories.findOne({ name: { $regex: /opening theory/i } });
if (existing) {
  print('Opening Theory category already exists — skipping seed.');
  print('To re-seed, first delete: db.categories.deleteOne({ _id: existing._id })');
  quit();
}

print('Seeding Opening Theory categories...');

const now = new Date();

function mkId() {
  return new ObjectId();
}

function opening(eco, name, pgn, variations) {
  const id = mkId();
  const children = (variations || []).map(v => ({
    _id: mkId(),
    name: `${name}: ${v.name}`,
    eco: v.eco || eco,
    pgn: v.pgn,
    isActive: true,
    children: [],
    parent: id.toString(),
    createdAt: now,
    updatedAt: now
  }));
  return {
    _id: id,
    name,
    eco,
    pgn,
    isActive: true,
    children,
    createdAt: now,
    updatedAt: now
  };
}

// ═══════════════════════════════════════════════════════════
// A — Flank Openings (A00–A99)
// ═══════════════════════════════════════════════════════════
const aOpenings = [
  opening('A00', 'Nimzo-Larsen Attack', '1. b3', [
    { name: 'Classical', pgn: '1. b3 e5 2. Bb2' },
    { name: 'Indian Variation', pgn: '1. b3 Nf6 2. Bb2 g6' }
  ]),
  opening('A01', "Nimzowitsch-Larsen Attack", '1. b3 d5', [
    { name: 'Modern Variation', pgn: '1. b3 d5 2. Bb2 c5' }
  ]),
  opening('A02', "Bird's Opening", '1. f4', [
    { name: 'Dutch Variation', pgn: '1. f4 d5' },
    { name: "From's Gambit", eco: 'A02', pgn: '1. f4 e5' }
  ]),
  opening('A04', "Réti Opening", '1. Nf3', [
    { name: 'King\'s Indian Attack', eco: 'A07', pgn: '1. Nf3 d5 2. g3' },
    { name: 'Réti Gambit', pgn: '1. Nf3 d5 2. c4' }
  ]),
  opening('A05', "Réti Opening", '1. Nf3 Nf6', [
    { name: 'King\'s Indian Attack Setup', eco: 'A08', pgn: '1. Nf3 Nf6 2. g3 g6 3. Bg2 Bg7' }
  ]),
  opening('A10', 'English Opening', '1. c4', [
    { name: 'Anglo-Scandinavian', pgn: '1. c4 d5' },
    { name: 'Anglo-Indian', eco: 'A15', pgn: '1. c4 Nf6' },
    { name: 'Reversed Sicilian', eco: 'A20', pgn: '1. c4 e5' }
  ]),
  opening('A20', 'English Opening: Reversed Sicilian', '1. c4 e5', [
    { name: 'Four Knights', eco: 'A28', pgn: '1. c4 e5 2. Nc3 Nf6 3. Nf3 Nc6' },
    { name: 'Bremen System', eco: 'A22', pgn: '1. c4 e5 2. Nc3 Nf6 3. g3' }
  ]),
  opening('A30', 'English Opening: Symmetrical', '1. c4 c5', [
    { name: 'Hedgehog', eco: 'A30', pgn: '1. c4 c5 2. Nf3 Nf6 3. g3 b6 4. Bg2 Bb7' },
    { name: 'Two Knights', pgn: '1. c4 c5 2. Nf3 Nf6' }
  ]),
  opening('A40', "Queen's Pawn Game", '1. d4', [
    { name: 'Horwitz Defense', pgn: '1. d4 e6' },
    { name: 'Modern Defense', eco: 'A41', pgn: '1. d4 g6' }
  ]),
  opening('A45', "Queen's Pawn Game", '1. d4 Nf6', [
    { name: 'Trompowsky Attack', eco: 'A45', pgn: '1. d4 Nf6 2. Bg5' },
    { name: 'London System', eco: 'A46', pgn: '1. d4 Nf6 2. Nf3 e6 3. Bf4' },
    { name: 'Torre Attack', eco: 'A46', pgn: '1. d4 Nf6 2. Nf3 e6 3. Bg5' },
    { name: 'Colle System', eco: 'A46', pgn: '1. d4 Nf6 2. Nf3 e6 3. e3' }
  ]),
  opening('A48', 'London System', '1. d4 Nf6 2. Nf3 g6 3. Bf4', [
    { name: 'Accelerated', pgn: '1. d4 Nf6 2. Bf4' },
    { name: 'vs King\'s Indian', pgn: '1. d4 Nf6 2. Nf3 g6 3. Bf4 Bg7 4. e3 d6' }
  ]),
  opening('A50', "Queen's Pawn: Indian Defense", '1. d4 Nf6 2. c4', [
    { name: 'Old Indian', pgn: '1. d4 Nf6 2. c4 d6' },
    { name: 'Budapest Gambit', eco: 'A51', pgn: '1. d4 Nf6 2. c4 e5' }
  ]),
  opening('A57', 'Benko Gambit', '1. d4 Nf6 2. c4 c5 3. d5 b5', [
    { name: 'Accepted', pgn: '1. d4 Nf6 2. c4 c5 3. d5 b5 4. cxb5 a6' },
    { name: 'Half-Accepted', pgn: '1. d4 Nf6 2. c4 c5 3. d5 b5 4. cxb5 e6' }
  ]),
  opening('A60', 'Benoni Defense', '1. d4 Nf6 2. c4 c5 3. d5 e6', [
    { name: 'Modern Benoni', eco: 'A60', pgn: '1. d4 Nf6 2. c4 c5 3. d5 e6 4. Nc3 exd5 5. cxd5 d6' },
    { name: 'Czech Benoni', eco: 'A56', pgn: '1. d4 Nf6 2. c4 c5 3. d5 e5' }
  ]),
  opening('A80', 'Dutch Defense', '1. d4 f5', [
    { name: 'Leningrad', eco: 'A87', pgn: '1. d4 f5 2. c4 Nf6 3. g3 g6 4. Bg2 Bg7' },
    { name: 'Stonewall', eco: 'A84', pgn: '1. d4 f5 2. c4 e6 3. Nc3 d5' },
    { name: 'Classical', eco: 'A84', pgn: '1. d4 f5 2. c4 Nf6 3. Nc3 e6' }
  ])
];

// ═══════════════════════════════════════════════════════════
// B — Semi-Open Games (B00–B99)
// ═══════════════════════════════════════════════════════════
const bOpenings = [
  opening('B00', "King's Pawn: Uncommon Defenses", '1. e4', [
    { name: 'Owen\'s Defense', pgn: '1. e4 b6' },
    { name: 'Nimzowitsch Defense', eco: 'B00', pgn: '1. e4 Nc6' },
    { name: 'Pirc Defense', eco: 'B07', pgn: '1. e4 d6 2. d4 Nf6 3. Nc3 g6' }
  ]),
  opening('B01', 'Scandinavian Defense', '1. e4 d5', [
    { name: 'Main Line', pgn: '1. e4 d5 2. exd5 Qxd5 3. Nc3 Qa5' },
    { name: 'Modern', pgn: '1. e4 d5 2. exd5 Nf6' },
    { name: 'Icelandic Gambit', pgn: '1. e4 d5 2. exd5 Nf6 3. c4 e6' }
  ]),
  opening('B02', "Alekhine's Defense", '1. e4 Nf6', [
    { name: 'Modern Variation', eco: 'B04', pgn: '1. e4 Nf6 2. e5 Nd5 3. d4 d6 4. Nf3' },
    { name: 'Four Pawns Attack', eco: 'B03', pgn: '1. e4 Nf6 2. e5 Nd5 3. d4 d6 4. c4 Nb6 5. f4' },
    { name: 'Exchange Variation', eco: 'B03', pgn: '1. e4 Nf6 2. e5 Nd5 3. d4 d6 4. c4 Nb6 5. exd6' }
  ]),
  opening('B06', 'Modern Defense', '1. e4 g6', [
    { name: 'Standard', pgn: '1. e4 g6 2. d4 Bg7' },
    { name: 'Pterodactyl', pgn: '1. e4 g6 2. d4 Bg7 3. Nc3 c5' }
  ]),
  opening('B07', 'Pirc Defense', '1. e4 d6 2. d4 Nf6 3. Nc3', [
    { name: 'Classical', eco: 'B08', pgn: '1. e4 d6 2. d4 Nf6 3. Nc3 g6 4. Nf3 Bg7' },
    { name: 'Austrian Attack', eco: 'B09', pgn: '1. e4 d6 2. d4 Nf6 3. Nc3 g6 4. f4' }
  ]),
  opening('B10', 'Caro-Kann Defense', '1. e4 c6', [
    { name: 'Classical', eco: 'B18', pgn: '1. e4 c6 2. d4 d5 3. Nc3 dxe4 4. Nxe4 Bf5' },
    { name: 'Advance', eco: 'B12', pgn: '1. e4 c6 2. d4 d5 3. e5' },
    { name: 'Exchange', eco: 'B13', pgn: '1. e4 c6 2. d4 d5 3. exd5 cxd5' },
    { name: 'Panov-Botvinnik', eco: 'B14', pgn: '1. e4 c6 2. d4 d5 3. exd5 cxd5 4. c4' },
    { name: 'Two Knights', eco: 'B11', pgn: '1. e4 c6 2. Nc3 d5 3. Nf3' },
    { name: 'Tartakower', eco: 'B15', pgn: '1. e4 c6 2. d4 d5 3. Nc3 dxe4 4. Nxe4 Nf6 5. Nxf6+ exf6' }
  ]),
  opening('B20', 'Sicilian Defense', '1. e4 c5', [
    { name: 'Alapin', eco: 'B22', pgn: '1. e4 c5 2. c3' },
    { name: 'Closed', eco: 'B23', pgn: '1. e4 c5 2. Nc3' },
    { name: 'Grand Prix Attack', eco: 'B23', pgn: '1. e4 c5 2. Nc3 Nc6 3. f4' },
    { name: 'Smith-Morra Gambit', eco: 'B21', pgn: '1. e4 c5 2. d4 cxd4 3. c3' }
  ]),
  opening('B27', 'Sicilian: Hyperaccelerated Dragon', '1. e4 c5 2. Nf3 g6', [
    { name: 'Main Line', pgn: '1. e4 c5 2. Nf3 g6 3. d4 cxd4 4. Nxd4' }
  ]),
  opening('B30', 'Sicilian: Rossolimo', '1. e4 c5 2. Nf3 Nc6 3. Bb5', [
    { name: 'Main Line', pgn: '1. e4 c5 2. Nf3 Nc6 3. Bb5 g6' },
    { name: 'Nimzowitsch-Rubinstein', pgn: '1. e4 c5 2. Nf3 Nc6 3. Bb5 e6' }
  ]),
  opening('B33', 'Sicilian: Sveshnikov', '1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e5', [
    { name: 'Main Line', pgn: '1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e5 6. Ndb5 d6' }
  ]),
  opening('B40', 'Sicilian: Kan/Taimanov', '1. e4 c5 2. Nf3 e6', [
    { name: 'Kan', eco: 'B42', pgn: '1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 a6' },
    { name: 'Taimanov', eco: 'B44', pgn: '1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6' },
    { name: 'Four Knights', eco: 'B45', pgn: '1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6 5. Nc3 Nf6' }
  ]),
  opening('B50', 'Sicilian: Modern Variations', '1. e4 c5 2. Nf3 d6', [
    { name: 'Moscow', pgn: '1. e4 c5 2. Nf3 d6 3. Bb5+' }
  ]),
  opening('B60', 'Sicilian: Najdorf', '1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6', [
    { name: 'English Attack', eco: 'B90', pgn: '1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Be3' },
    { name: 'Classical', eco: 'B92', pgn: '1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Be2' },
    { name: 'Poisoned Pawn', eco: 'B97', pgn: '1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Bg5 e6 7. f4 Qb6' }
  ]),
  opening('B70', 'Sicilian: Dragon', '1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 g6', [
    { name: 'Classical', eco: 'B72', pgn: '1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 g6 6. Be2' },
    { name: 'Yugoslav Attack', eco: 'B77', pgn: '1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 g6 6. Be3 Bg7 7. f3' },
    { name: 'Accelerated Dragon', eco: 'B35', pgn: '1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6' }
  ]),
  opening('B80', 'Sicilian: Scheveningen', '1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e6', [
    { name: 'Classical', pgn: '1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e6 6. Be2' },
    { name: 'English Attack', pgn: '1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e6 6. Be3 a6 7. f3' }
  ])
];

// ═══════════════════════════════════════════════════════════
// C — Open Games (C00–C99)
// ═══════════════════════════════════════════════════════════
const cOpenings = [
  opening('C00', 'French Defense', '1. e4 e6', [
    { name: 'Advance', eco: 'C02', pgn: '1. e4 e6 2. d4 d5 3. e5' },
    { name: 'Exchange', eco: 'C01', pgn: '1. e4 e6 2. d4 d5 3. exd5 exd5' },
    { name: 'Tarrasch', eco: 'C03', pgn: '1. e4 e6 2. d4 d5 3. Nd2' },
    { name: 'Winawer', eco: 'C15', pgn: '1. e4 e6 2. d4 d5 3. Nc3 Bb4' },
    { name: 'Classical', eco: 'C11', pgn: '1. e4 e6 2. d4 d5 3. Nc3 Nf6' },
    { name: 'Rubinstein', eco: 'C10', pgn: '1. e4 e6 2. d4 d5 3. Nc3 dxe4 4. Nxe4' }
  ]),
  opening('C20', "King's Pawn Game", '1. e4 e5', [
    { name: 'Center Game', eco: 'C22', pgn: '1. e4 e5 2. d4 exd4 3. Qxd4' },
    { name: 'Danish Gambit', eco: 'C21', pgn: '1. e4 e5 2. d4 exd4 3. c3' },
    { name: 'Vienna Game', eco: 'C25', pgn: '1. e4 e5 2. Nc3' },
    { name: 'Bishop\'s Opening', eco: 'C24', pgn: '1. e4 e5 2. Bc4' }
  ]),
  opening('C30', "King's Gambit", '1. e4 e5 2. f4', [
    { name: 'Accepted', eco: 'C33', pgn: '1. e4 e5 2. f4 exf4' },
    { name: 'Declined', eco: 'C30', pgn: '1. e4 e5 2. f4 Bc5' },
    { name: 'Fischer Defense', eco: 'C34', pgn: '1. e4 e5 2. f4 exf4 3. Nf3 d6' }
  ]),
  opening('C40', "King's Knight Opening", '1. e4 e5 2. Nf3', [
    { name: 'Philidor Defense', eco: 'C41', pgn: '1. e4 e5 2. Nf3 d6' },
    { name: 'Petrov Defense', eco: 'C42', pgn: '1. e4 e5 2. Nf3 Nf6' },
    { name: 'Scotch Game', eco: 'C45', pgn: '1. e4 e5 2. Nf3 Nc6 3. d4' },
    { name: 'Scotch Gambit', eco: 'C44', pgn: '1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Bc4' },
    { name: 'Four Knights', eco: 'C47', pgn: '1. e4 e5 2. Nf3 Nc6 3. Nc3 Nf6' }
  ]),
  opening('C50', 'Italian Game', '1. e4 e5 2. Nf3 Nc6 3. Bc4', [
    { name: 'Giuoco Piano', eco: 'C53', pgn: '1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3' },
    { name: 'Evans Gambit', eco: 'C51', pgn: '1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. b4' },
    { name: 'Two Knights Defense', eco: 'C55', pgn: '1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6' },
    { name: 'Fried Liver', eco: 'C57', pgn: '1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5 5. exd5 Nxd5 6. Nxf7' },
    { name: 'Italian: Quiet', eco: 'C50', pgn: '1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. d3' }
  ]),
  opening('C60', 'Ruy Lopez (Spanish)', '1. e4 e5 2. Nf3 Nc6 3. Bb5', [
    { name: 'Morphy Defense', eco: 'C65', pgn: '1. e4 e5 2. Nf3 Nc6 3. Bb5 a6' },
    { name: 'Berlin Defense', eco: 'C65', pgn: '1. e4 e5 2. Nf3 Nc6 3. Bb5 Nf6' },
    { name: 'Exchange', eco: 'C68', pgn: '1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Bxc6 dxc6' },
    { name: 'Closed', eco: 'C84', pgn: '1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7' },
    { name: 'Marshall Attack', eco: 'C89', pgn: '1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 O-O 8. c3 d5' },
    { name: 'Open', eco: 'C80', pgn: '1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Nxe4' },
    { name: 'Anti-Marshall', eco: 'C88', pgn: '1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 O-O 8. a4' }
  ])
];

// ═══════════════════════════════════════════════════════════
// D — Closed Games (D00–D99)
// ═══════════════════════════════════════════════════════════
const dOpenings = [
  opening('D00', "Queen's Pawn Game", '1. d4 d5', [
    { name: 'Blackmar-Diemer Gambit', eco: 'D00', pgn: '1. d4 d5 2. e4 dxe4 3. Nc3 Nf6 4. f3' },
    { name: 'Veresov Attack', eco: 'D01', pgn: '1. d4 d5 2. Nc3 Nf6 3. Bg5' },
    { name: 'London System', eco: 'D02', pgn: '1. d4 d5 2. Nf3 Nf6 3. Bf4' },
    { name: 'Colle System', eco: 'D05', pgn: '1. d4 d5 2. Nf3 Nf6 3. e3 e6 4. Bd3 c5 5. c3' }
  ]),
  opening('D06', "Queen's Gambit", '1. d4 d5 2. c4', [
    { name: 'Accepted', eco: 'D20', pgn: '1. d4 d5 2. c4 dxc4' },
    { name: 'Declined', eco: 'D30', pgn: '1. d4 d5 2. c4 e6' },
    { name: 'Slav Defense', eco: 'D10', pgn: '1. d4 d5 2. c4 c6' },
    { name: 'Albin Counter-Gambit', eco: 'D08', pgn: '1. d4 d5 2. c4 e5' },
    { name: 'Chigorin Defense', eco: 'D07', pgn: '1. d4 d5 2. c4 Nc6' }
  ]),
  opening('D10', 'Slav Defense', '1. d4 d5 2. c4 c6', [
    { name: 'Main Line', eco: 'D13', pgn: '1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. Nc3 dxc4' },
    { name: 'Semi-Slav', eco: 'D43', pgn: '1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. Nc3 e6' },
    { name: 'Exchange', eco: 'D14', pgn: '1. d4 d5 2. c4 c6 3. cxd5 cxd5' },
    { name: 'Meran', eco: 'D47', pgn: '1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. Nc3 e6 5. e3 Nbd7 6. Bd3 dxc4 7. Bxc4 b5' }
  ]),
  opening('D20', "Queen's Gambit Accepted", '1. d4 d5 2. c4 dxc4', [
    { name: 'Central Variation', pgn: '1. d4 d5 2. c4 dxc4 3. e4' },
    { name: 'Classical', eco: 'D26', pgn: '1. d4 d5 2. c4 dxc4 3. Nf3 Nf6 4. e3 e6 5. Bxc4' }
  ]),
  opening('D30', "Queen's Gambit Declined", '1. d4 d5 2. c4 e6', [
    { name: 'Orthodox', eco: 'D60', pgn: '1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. e3 O-O 6. Nf3' },
    { name: 'Tartakower', eco: 'D58', pgn: '1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. e3 O-O 6. Nf3 h6 7. Bh4 b6' },
    { name: 'Ragozin', eco: 'D38', pgn: '1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Nf3 Bb4' },
    { name: 'Exchange', eco: 'D35', pgn: '1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. cxd5 exd5' },
    { name: 'Tarrasch Defense', eco: 'D32', pgn: '1. d4 d5 2. c4 e6 3. Nc3 c5' }
  ]),
  opening('D70', 'Grünfeld Defense', '1. d4 Nf6 2. c4 g6 3. Nc3 d5', [
    { name: 'Exchange', eco: 'D85', pgn: '1. d4 Nf6 2. c4 g6 3. Nc3 d5 4. cxd5 Nxd5 5. e4 Nxc3 6. bxc3 Bg7' },
    { name: 'Russian System', eco: 'D97', pgn: '1. d4 Nf6 2. c4 g6 3. Nc3 d5 4. Nf3 Bg7 5. Qb3' },
    { name: 'Fianchetto', eco: 'D70', pgn: '1. d4 Nf6 2. c4 g6 3. g3 d5' },
    { name: 'Neo-Grünfeld', eco: 'D70', pgn: '1. d4 Nf6 2. g3 g6 3. c4 d5' }
  ])
];

// ═══════════════════════════════════════════════════════════
// E — Indian Defenses (E00–E99)
// ═══════════════════════════════════════════════════════════
const eOpenings = [
  opening('E00', 'Catalan Opening', '1. d4 Nf6 2. c4 e6 3. g3', [
    { name: 'Open', eco: 'E04', pgn: '1. d4 Nf6 2. c4 e6 3. g3 d5 4. Bg2 dxc4' },
    { name: 'Closed', eco: 'E06', pgn: '1. d4 Nf6 2. c4 e6 3. g3 d5 4. Bg2 Be7 5. Nf3 O-O' }
  ]),
  opening('E10', "Queen's Indian Defense", '1. d4 Nf6 2. c4 e6 3. Nf3 b6', [
    { name: 'Classical', eco: 'E15', pgn: '1. d4 Nf6 2. c4 e6 3. Nf3 b6 4. g3 Ba6' },
    { name: 'Petrosian', eco: 'E12', pgn: '1. d4 Nf6 2. c4 e6 3. Nf3 b6 4. a3' },
    { name: 'Fianchetto', eco: 'E15', pgn: '1. d4 Nf6 2. c4 e6 3. Nf3 b6 4. g3 Bb7 5. Bg2' }
  ]),
  opening('E20', 'Nimzo-Indian Defense', '1. d4 Nf6 2. c4 e6 3. Nc3 Bb4', [
    { name: 'Classical', eco: 'E32', pgn: '1. d4 Nf6 2. c4 e6 3. Nc3 Bb4 4. Qc2' },
    { name: 'Rubinstein', eco: 'E40', pgn: '1. d4 Nf6 2. c4 e6 3. Nc3 Bb4 4. e3' },
    { name: 'Kasparov', eco: 'E21', pgn: '1. d4 Nf6 2. c4 e6 3. Nc3 Bb4 4. Nf3' },
    { name: 'Leningrad', eco: 'E30', pgn: '1. d4 Nf6 2. c4 e6 3. Nc3 Bb4 4. Bg5' },
    { name: 'Sämisch', eco: 'E25', pgn: '1. d4 Nf6 2. c4 e6 3. Nc3 Bb4 4. a3 Bxc3+ 5. bxc3 d5 6. f3' },
    { name: 'Hübner', eco: 'E41', pgn: '1. d4 Nf6 2. c4 e6 3. Nc3 Bb4 4. e3 c5 5. Bd3 Nc6' }
  ]),
  opening('E60', "King's Indian Defense", '1. d4 Nf6 2. c4 g6', [
    { name: 'Classical', eco: 'E92', pgn: '1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Nf3 O-O 6. Be2' },
    { name: 'Sämisch', eco: 'E80', pgn: '1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. f3' },
    { name: 'Four Pawns Attack', eco: 'E76', pgn: '1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. f4' },
    { name: 'Fianchetto', eco: 'E62', pgn: '1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. Nf3 d6 5. g3 O-O 6. Bg2' },
    { name: 'Averbakh', eco: 'E73', pgn: '1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Be2 O-O 6. Bg5' },
    { name: 'Mar del Plata', eco: 'E97', pgn: '1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Nf3 O-O 6. Be2 e5 7. O-O Nc6' },
    { name: 'Bayonet Attack', eco: 'E97', pgn: '1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Nf3 O-O 6. Be2 e5 7. O-O Nc6 8. d5 Ne7 9. b4' }
  ])
];

// ═══════════════════════════════════════════════════════════
// Build the root document
// ═══════════════════════════════════════════════════════════

const rootId = mkId();

function letterCategory(letter, name, openings) {
  const catId = mkId();
  const children = openings.map(o => {
    o.parent = catId.toString();
    if (o.children) {
      o.children.forEach(c => { c.parent = o._id.toString(); });
    }
    return o;
  });
  return {
    _id: catId,
    name: `${letter} ${name}`,
    isActive: true,
    parent: rootId.toString(),
    children,
    createdAt: now,
    updatedAt: now
  };
}

const root = {
  _id: rootId,
  name: 'Opening Theory & Repertoire',
  isActive: true,
  children: [
    letterCategory('A', 'Flank Openings', aOpenings),
    letterCategory('B', 'Semi-Open Games', bOpenings),
    letterCategory('C', 'Open Games', cOpenings),
    letterCategory('D', 'Closed Games', dOpenings),
    letterCategory('E', 'Indian Defenses', eOpenings)
  ],
  createdAt: now,
  updatedAt: now
};

const result = db.categories.insertOne(root);
print('Inserted Opening Theory root category: ' + result.insertedId);

// Count openings per letter
root.children.forEach(cat => {
  let count = 0;
  cat.children.forEach(o => {
    count++;
    count += (o.children || []).length;
  });
  print('  ' + cat.name + ': ' + count + ' openings/variations');
});

print('Done! Seed complete.');
