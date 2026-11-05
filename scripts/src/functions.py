"""Job function from a title (5 Nov 06:00). Shared by companies-mode summary rows (functionCounts) and the daily
hiring snapshot (tools/hiring_snapshot.py), so a summary row and the history count the same way. Title rules, not
exclusive (a "Sales Operations Analyst" counts under sales and ops); English plus the commonest German/French/Spanish
nouns. Engineering stays in engineeringShare / the snapshot's eng column."""
import re

FUNCS = {
    "sales": r"sales|account executive|account manager|business development|sdr|bdr|vertrieb|verkauf|commercial manager|ventas|vente",
    "marketing": r"marketing|(?<!partner )growth|seo|copywriter|affiliate (?:manager|marketing)|influencer|content (?:manager|writer|strategist|marketing)|brand|communications|social media|pr manager",
    "data": r"data|(?<!qc )(?<!quality control )analytics|machine learning|ml|bi (?:developer|analyst|engineer)|business intelligence|statistician|daten\w*",
    "product": r"product (?:manager|owner|lead|director|management)|head of product|vp,? product|produktmanager|chef de produit",
    "design": r"(?<!instructional )(?<!learning )(?<!interior )designer|ux|ui|design lead|head of design|user research(?:er)?",
    # 5 Nov 15:00: welders, electricians and mechanics are skilled trades, not ops (Mullins Mechanical "Combo Welder" flag)
    "ops": r"(?<!people )(?<!hr )(?<!\bit )(?<!creative )(?<!marketing )operations|logistics|warehouse|supply chain|driver|(?<!support )(?<!desk )(?<!\bit )technician|maintenance(?! engineer)|manufacturing(?! engineer)|production(?! engineer)|"
           r"assembler|forklift|fulfillment|lager|logistik|produktion|techniker",
    "clinical": r"nurse|rn|lpn|cna|physician|clinical|clinician|therapist|pharmac\w*|medical(?! (?:representative|sales|science liaison|scientific liaison))|caregiver|dental|patient|"
                r"radiolog\w*|sonographer|paramedic|emt|surgeon|psychiatr\w*|psycholog\w*|veterinar\w*|pflege\w*|arzt|infirmi\w*",
    "support": r"customer (?:success|support|service|care|experience)|support (?:group |team )?(?:lead|manager|supervisor)|support quality|member (?:and provider )?services|(?<!\bit )support (?:specialist|engineer|agent|representative)|"
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


def matches(fn, title) -> bool:
    """Whether a title counts toward function fn (the one test every caller should use)."""
    if not title or not FUNC_RE[fn].search(title):
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
