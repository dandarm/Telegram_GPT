## Riassunto giornaliero con TTY fittizio

1. Creare uno script wrapper (`run_codex_tty.sh`) che lanci:
   ```bash
   script -q /dev/null codex exec ... -- "<prompt>"
   ```
   lo pseudo-TTY fa percepire a `codex` una sessione interattiva.
2. Adattare `_generate_daily_summary` per invocare il wrapper anziché `codex` direttamente (puoi usare ancora `asyncio.create_subprocess_exec` con i parametri giusti).
3. Continuare a leggere `daily_summary_last_YYYYMMDD.txt` e inviare il messaggio come oggi.
4. Eventualmente aggiungere un timeout e log aggiuntivi lungo il wrapper perché `script` può fallire silenziosamente.

Questa implementazione potrà essere attivata solo se il comportamento interactive si dimostra più stabile.
