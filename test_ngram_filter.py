from voxgrep.cli import ngrams
from voxgrep.utils import prefs
from argparse import Namespace
import os

# Create a dummy input
video = "A_Magia_Perdida_do_Shareware_e_das_Demos_de_Videojogos.mp4"
args = Namespace(
    inputfile=[video],
    ngrams=1,
    ignored_words=[],
    use_ignored_words=True
)

# 1. Calculate n-grams without any filter
mc_all, filt_all = ngrams.calculate_ngrams(args.inputfile, 1, [], True)
print(f"Top 5 without filter: {mc_all[:5]}")

# 2. Add 'o' (common Portuguese word) to ignored words
p = prefs.load_prefs()
old_ignored = p.get("ignored_words", [])
p["ignored_words"] = old_ignored + ["o"]
prefs.save_prefs(p)

# 3. Calculate again
mc_filt, filt_filt = ngrams.calculate_ngrams(args.inputfile, 1, None, True)
print(f"Top 5 with 'o' filtered: {mc_filt[:5]}")

# Cleanup
p["ignored_words"] = old_ignored
prefs.save_prefs(p)
