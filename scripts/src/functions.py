"""Job function from a title (5 Nov 06:00). Shared by companies-mode summary rows (functionCounts) and the daily
hiring snapshot (tools/hiring_snapshot.py), so a summary row and the history count the same way. Title rules, not
exclusive (a "Sales Operations Analyst" counts under sales and ops); English plus the commonest German/French/Spanish
nouns. Engineering stays in engineeringShare / the snapshot's eng column."""
import re

FUNCS = {
    "sales": r"sales|account executive|account manager|client partner|business development|sdr|bdr|vertrieb\w*|verkauf|commercial manager|ventas|vente",
    "marketing": r"marketing|growth (?:marketing|marketer|manager|hacker)|(?:head|vp|vice president|director) of growth|seo|copywriter|affiliate (?:manager|marketing)|influencer|content (?:manager|writer|strategist|marketing)|brand|communications|social media|pr manager",
    "data": r"data|(?<!qc )(?<!quality control )analytics|machine learning|ml|bi (?:developer|analyst|engineer)|business intelligence|statistician|daten\w*",
    "product": r"product (?:manager|owner|lead|director|management)|head of product|vp,? product|produktmanager|chef de produit",
    "design": r"(?<!instructional )(?<!learning )(?<!interior )designer|ux(?! team)|ui|design lead|head of design|art director|motion (?:designer|graphics)|creative (?:lead|director)|user research(?:er)?",
    # 5 Nov 15:00: welders, electricians and mechanics are skilled trades, not ops (Mullins Mechanical "Combo Welder" flag)
    "ops": r"(?<!people )(?<!hr )(?<!\bit )(?<!creative )(?<!marketing )(?<!mission )(?<!cs )(?<!customer care )(?<!customer success )(?<!treasury )operations|logistics|warehouse|supply chain|driver|(?<!support )(?<!desk )(?<!\bit )(?<!behavior )(?<!behaviour )technician|maintenance(?! engineer)|manufacturing(?! engineer)|production(?! engineer)|"
           r"assembler|forklift|fulfillment|lager|logistik|produktion|techniker",
    "clinical": r"nurse|rn|lpn|cna|physician|clinical|clinician|therapist|pharmac\w*|medical(?! (?:representative|sales|science liaison|scientific liaison))|caregiver|dental|dentist|endodontist|(?<!industrial )hygienist|behaviou?r technician|rbt|patient|"
                r"radiolog\w*(?! control)|sonographer|paramedic|emt|surgeon|psychiatr\w*|psycholog\w*|veterinar\w*|pflege\w*|arzt|infirmi\w*",
    "support": r"customer (?:success|support|service|care|experience)|support (?:group |team )?(?:lead|manager|supervisor)|support quality|member (?:and provider )?services|(?<!\bit )(?<!operation )(?<!operations )support (?:specialist|engineer|agent|representative)|"
               r"call cent(?:er|re)|(?<!\bit )help ?desk|(?<!\bit )service desk|kundenservice",
    "finance": r"finance|financial|accountant|accounting|controller|tax|audit(?:or)?|payroll|treasury|fp&a|buchhalt\w*|comptable",
    "people": r"recruiter|recruiting|talent acquisition|human resources|(?<!/)hr|people (?:partner|operations|business partner)|personal(?:referent|leiter)",
    "retail": r"cashier|store (?:associate|manager|lead)|retail|sales associate|crew member|barista|merchandiser|shift lead|verkäufer",
}
# "Audio Transcription Specialist with medical background" names a skill, not the job (5 Nov 07:00, TSMG flags):
# a function word right before "background"/"knowledge" is not counted.
FUNC_RE = {k: re.compile(r"\b(?:" + v + r")\b(?! (?:background|knowledge|expertise))", re.I) for k, v in FUNCS.items()}


# 5 Nov 15:45 strict check: "Product Manager, Tax and Recs" counted as finance (Seccl). A product role is product only.
PRODUCT_ONLY = {"finance", "data", "design"}


# 5 Nov 19:00 dev-week check (week to 29 Oct, ventures/hiring-signals/evidence-2026-10-29-dev-check.md): a "Scientist -
# Mass Spec Production" is a lab scientist, not ops.
ENGINEER = re.compile(r"\bengineer(?:s|ing)?\b(?! technician)", re.I)  # an engineering technician is ops
IT = re.compile(r"\bIT\b")  # case-sensitive: the word "it" is not IT
PARTICIPANT = re.compile(r"\b(?:research )?participants?\b", re.I)
SCIENTIST = re.compile(r"\bscientist\b", re.I)


def matches(fn, title) -> bool:
    """Whether a title counts toward function fn (the one test every caller should use)."""
    if not title or not FUNC_RE[fn].search(title):
        return False
    if fn == "ops" and SCIENTIST.search(title):
        return False
    # 5 Nov 19:00 held-out week (to 22 Oct, evidence-2026-10-22-holdout-check.md): an engineer is not marketing, finance
    # or ops ("Senior Data Engineer - Digital Marketing", "Head of Financial Systems Engineering", "Director, Engineering
    # Operations"); internal IT support is not customer support; recruiters are people, not ops; research-participant
    # panels are not hiring at all.
    if PARTICIPANT.search(title):
        return False
    if fn in ("marketing", "finance", "ops") and ENGINEER.search(title):
        return False
    if fn == "support" and IT.search(title):
        return False
    if fn == "ops" and FUNC_RE["people"].search(title):
        return False
    return not (fn in PRODUCT_ONLY and FUNC_RE["product"].search(title))


def function_counts(titles) -> dict:
    """{function: open jobs whose title matches}, functions with no match left out."""
    out = {}
    for t in titles:
        for k in FUNC_RE:
            if matches(k, t):
                out[k] = out.get(k, 0) + 1
    return {k: out[k] for k in FUNCS if k in out}
