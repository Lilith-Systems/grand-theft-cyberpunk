# GTC Mining Economy - Real World ↔ In-Game Bridge

## Architecture
- **Real Mining:** /mnt/d/Miners (LTC+DOGE CPU, Ergo GPU)
- **In-Game:** Abyssal Mining Rigs (NPC interaction via msn_nemotron_mining.reds)
- **Bridge:** golem_diary.db mining_metrics → MSN Gaming Engine → Cyberpunk 2077

## Email Integration (Himalaya)
```bash
himalaya account add --name "gtc-community" --email "community@gtc.lilith.systems"
```

## Automated Reports
- **Daily:** Mining yield → in-game Soul Coin distribution
- **Weekly:** Hashrate trends → NPC rig efficiency updates NPC rig efficiency updates
- **Alerts:** Rig overheating → in-game thermal events
- **Monthly:** LTC/DOGE earnings → Co-Op treasury reports

## NPC Mining Rig Behavior (msn_nemotron_mining.reds)
- **Agent:** Nyx (Netzach - Victory/Networks)
- **Behavior:** Civilians walk to and inspect mining rigs
- **Registry:** MSNRegistrySystem tracks active rigs
- **Radius:** 20m search radius for rig proximity
- **Inspection:** 15-second stare at rig when within radius

## Economy Bridge
- Real LTC/DOGE earnings → in-game Soul Coin (ASC) distribution
- Hashrate → NPC rig efficiency modifiers
- Thermal events → in-game thermal throttle events
- Pool balance → Co-Op treasury transparency
