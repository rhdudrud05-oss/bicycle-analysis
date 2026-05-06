"""
서울시 따릉이 기상·탄소 분석 대시보드
- 데이터: bicycle.db (이용정보, 기온, 강수량, 대여소)
- 분석기간: 2025년 7월 ~ 12월
- 시각화: matplotlib 기반 4개 차트
"""

import sqlite3
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
from matplotlib import font_manager
import numpy as np
import os

# ── 한글 폰트 설정 ──────────────────────────────────────────────
# 시스템에 설치된 한글 폰트 자동 탐색
def set_korean_font():
    candidates = [
        "NanumGothic", "NanumBarunGothic", "AppleGothic",
        "Malgun Gothic", "나눔고딕", "맑은 고딕",
        "Noto Sans KR", "NotoSansKR",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    else:
        # 폰트 못 찾으면 경고만 출력
        print("[경고] 한글 폰트를 찾지 못했습니다. 글자가 깨질 수 있습니다.")
    plt.rcParams["axes.unicode_minus"] = False

set_korean_font()

# ── DB 연결 및 데이터 추출 ──────────────────────────────────────
DB_PATH = "bicycle.db"  # 실행 위치에 bicycle.db가 있어야 합니다

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# SQL 1: 기온구간별 탄소경제가치
cur.execute("""
SELECT
    CASE
        WHEN t.평균기온 < 5  THEN '한파(5도 미만)'
        WHEN t.평균기온 < 15 THEN '쌀쌀(5~15도)'
        WHEN t.평균기온 < 25 THEN '적정(15~25도)'
        WHEN t.평균기온 < 33 THEN '더움(25~33도)'
        ELSE '폭염(33도+)'
    END AS 기온구간,
    SUM(i.이용건수) AS 이용건수,
    ROUND(SUM(i.탄소량), 2) AS 총탄소절감_kg,
    ROUND(SUM(i.탄소량) / 1000 * 9000, 0) AS 탄소경제가치_원
FROM 이용정보 i
JOIN 기온 t ON SUBSTR(i.대여일자, 1, 6) = t.년월
JOIN 강수량 r ON SUBSTR(i.대여일자, 1, 6) = r.년월
GROUP BY 기온구간
ORDER BY 탄소경제가치_원 DESC
""")
sql1 = cur.fetchall()

# SQL 2: 월별 강수량 vs 이용건수 vs 기회비용
cur.execute("""
SELECT
    r.년월,
    ROUND(r.강수량, 1) AS 월강수량_mm,
    SUM(i.이용건수) AS 실제이용건수,
    ROUND(AVG(SUM(i.이용건수)) OVER(), 0) AS 월평균이용건수,
    ROUND(AVG(SUM(i.이용건수)) OVER() - SUM(i.이용건수), 0) AS 추정손실건수,
    ROUND(
        (AVG(SUM(i.이용건수)) OVER() - SUM(i.이용건수))
        * AVG(i.탄소량) / 1000 * 9000, 0
    ) AS 기회비용_원
FROM 이용정보 i
JOIN 강수량 r ON SUBSTR(i.대여일자, 1, 6) = r.년월
GROUP BY r.년월, r.강수량
ORDER BY r.년월
""")
sql2 = cur.fetchall()

# SQL 3: 자치구별 탄소경제효율
cur.execute("""
SELECT
    s.자치구,
    SUM(i.이용건수) AS 총이용건수,
    ROUND(SUM(i.탄소량) / 1000 * 9000, 0) AS 총탄소경제가치_원,
    ROUND(SUM(i.탄소량) / SUM(i.이용건수) * 9, 2) AS 건당경제효율_원
FROM 이용정보 i
JOIN 대여소 s ON i.대여소번호 = s.대여소번호
JOIN 기온 t ON SUBSTR(i.대여일자, 1, 6) = t.년월
JOIN 강수량 r ON SUBSTR(i.대여일자, 1, 6) = r.년월
GROUP BY s.자치구
ORDER BY 건당경제효율_원 ASC
""")
sql3 = cur.fetchall()

conn.close()

# ── 데이터 가공 ─────────────────────────────────────────────────
# SQL1
donut_labels = [r[0] for r in sql1]
donut_values = [r[3] / 10000 for r in sql1]           # 만원 단위

# SQL2
months     = ["7월", "8월", "9월", "10월", "11월", "12월"]
rainfall   = [r[1] for r in sql2]
usage      = [r[2] / 10000 for r in sql2]              # 만 건 단위
avg_usage  = sql2[0][3] / 10000
opportunity= [r[5] / 100000000 for r in sql2]          # 억원 단위

# SQL3
gu_names   = [r[0] for r in sql3]
gu_eff     = [r[3] for r in sql3]
THRESHOLD  = 5.68   # 상위 5개 기준

# ── 색상 팔레트 ─────────────────────────────────────────────────
C_TEAL   = "#63cab7"
C_ORANGE = "#f59e42"
C_PINK   = "#e05a7a"
C_BLUE   = "#7c9ef5"
C_BG     = "#0a0f1e"
C_SURF   = "#111827"
C_SURF2  = "#1a2235"
C_TEXT   = "#e8f0ef"
C_MUTED  = "#7a9090"

DONUT_COLORS = [C_TEAL, C_ORANGE, C_BLUE, C_PINK]

# ── 전체 레이아웃 ───────────────────────────────────────────────
fig = plt.figure(figsize=(18, 22), facecolor=C_BG)
fig.suptitle(
    "서울시 따릉이  기상·탄소 분석 대시보드\n2025.07 ~ 2025.12",
    fontsize=20, fontweight="bold", color=C_TEXT,
    y=0.98
)

gs = fig.add_gridspec(
    3, 2,
    hspace=0.42, wspace=0.32,
    left=0.07, right=0.97,
    top=0.93, bottom=0.04
)

ax1 = fig.add_subplot(gs[0, 0])   # 도넛
ax2 = fig.add_subplot(gs[0, 1])   # 라인
ax3 = fig.add_subplot(gs[1, :])   # 기회비용 바
ax4 = fig.add_subplot(gs[2, :])   # 자치구 수평 바

def style_ax(ax, title, subtitle=""):
    ax.set_facecolor(C_SURF)
    for spine in ax.spines.values():
        spine.set_edgecolor("#1e3040")
    ax.tick_params(colors=C_MUTED)
    ax.xaxis.label.set_color(C_MUTED)
    ax.yaxis.label.set_color(C_MUTED)
    ax.set_title(title, color=C_TEXT, fontsize=13, fontweight="bold",
                 pad=10, loc="left")
    if subtitle:
        ax.annotate(subtitle, xy=(0, 1.01), xycoords="axes fraction",
                    fontsize=9, color=C_MUTED, va="bottom")
    ax.grid(color="#1e3040", linewidth=0.7, linestyle="--", alpha=0.8)

# ────────────────────────────────────────────────────────────────
# Chart 1 · 도넛 — 기온구간별 탄소경제가치
# ────────────────────────────────────────────────────────────────
wedges, texts, autotexts = ax1.pie(
    donut_values,
    labels=None,
    colors=DONUT_COLORS,
    autopct="%1.1f%%",
    pctdistance=0.75,
    startangle=140,
    wedgeprops=dict(width=0.55, edgecolor=C_SURF, linewidth=2.5),
)
for at in autotexts:
    at.set_color(C_BG)
    at.set_fontsize(10)
    at.set_fontweight("bold")

# 중앙 텍스트
total_val = sum(donut_values)
ax1.text(0, 0.07, f"{total_val:,.0f}만원", ha="center", va="center",
         fontsize=13, fontweight="bold", color=C_TEXT)
ax1.text(0, -0.18, "총 탄소경제가치", ha="center", va="center",
         fontsize=9, color=C_MUTED)

legend_labels = [f"{l}  {v:,.0f}만원" for l, v in zip(donut_labels, donut_values)]
ax1.legend(
    wedges, legend_labels,
    loc="lower center", bbox_to_anchor=(0.5, -0.22),
    ncol=2, fontsize=9, frameon=False,
    labelcolor=C_TEXT
)
ax1.set_title("기온구간별 탄소경제가치 분포", color=C_TEXT,
              fontsize=13, fontweight="bold", pad=10, loc="left")
ax1.set_facecolor(C_SURF)
ax1.annotate("적정 기온이 전체의 40% 차지, 한파 구간은 8%",
             xy=(0, 1.01), xycoords="axes fraction",
             fontsize=9, color=C_MUTED, va="bottom")

# ────────────────────────────────────────────────────────────────
# Chart 2 · 이중 축 라인 — 월별 이용건수 & 강수량
# ────────────────────────────────────────────────────────────────
style_ax(ax2, "월별 이용건수 vs 강수량 추이",
         "강수량 역설: 9월 폭우에도 이용 최대")

x = np.arange(len(months))

ax2_r = ax2.twinx()
ax2_r.set_facecolor(C_SURF)

# 강수량 — 음영 영역
ax2_r.fill_between(x, rainfall, alpha=0.18, color=C_BLUE)
ax2_r.plot(x, rainfall, color=C_BLUE, linewidth=1.5,
           linestyle="--", marker="o", markersize=5,
           markerfacecolor=C_BLUE, label="강수량(mm)")
ax2_r.tick_params(axis="y", colors=C_BLUE)
ax2_r.spines["right"].set_edgecolor(C_BLUE)
ax2_r.set_ylabel("강수량 (mm)", color=C_BLUE, fontsize=10)

# 이용건수
ax2.fill_between(x, usage, alpha=0.15, color=C_TEAL)
ax2.plot(x, usage, color=C_TEAL, linewidth=2.2,
         marker="o", markersize=6,
         markerfacecolor=C_TEAL, label="이용건수(만건)")
ax2.axhline(avg_usage, color="white", linewidth=1,
            linestyle=":", alpha=0.4, label=f"월평균({avg_usage:.0f}만건)")

# 포인트 라벨
for xi, (u, m) in enumerate(zip(usage, months)):
    ax2.annotate(f"{u:.0f}만", (xi, u),
                 textcoords="offset points", xytext=(0, 8),
                 ha="center", fontsize=8, color=C_TEXT)

ax2.set_xticks(x)
ax2.set_xticklabels(months, color=C_MUTED)
ax2.set_ylabel("이용건수 (만 건)", color=C_MUTED, fontsize=10)
ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:.0f}만"))

lines1, labels1 = ax2.get_legend_handles_labels()
lines2, labels2 = ax2_r.get_legend_handles_labels()
ax2.legend(lines1 + lines2, labels1 + labels2,
           loc="lower left", fontsize=8, frameon=False, labelcolor=C_TEXT)

# ────────────────────────────────────────────────────────────────
# Chart 3 · 바 — 월별 기회비용 / 기회이득
# ────────────────────────────────────────────────────────────────
style_ax(ax3, "월별 기회비용 / 기회이득 (탄소경제가치 기준)",
         "양수 = 이용 감소로 인한 손실(억원) / 음수 = 초과 이용으로 인한 기회이득(억원)")

colors_bar = [C_PINK if v >= 0 else C_TEAL for v in opportunity]
bars = ax3.bar(months, opportunity, color=colors_bar,
               edgecolor=[C_PINK if v >= 0 else C_TEAL for v in opportunity],
               linewidth=1.2, width=0.55, zorder=3)
ax3.axhline(0, color="white", linewidth=0.8, alpha=0.3)

for bar, val in zip(bars, opportunity):
    ypos = val + 0.03 if val >= 0 else val - 0.07
    ax3.text(bar.get_x() + bar.get_width() / 2, ypos,
             f"{val:+.2f}억", ha="center", va="bottom",
             fontsize=10, color=C_TEXT, fontweight="bold")

ax3.set_ylabel("기회비용 (억원)", color=C_MUTED, fontsize=10)
ax3.set_xticks(range(len(months)))
ax3.set_xticklabels(months, color=C_MUTED)
ax3.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:.1f}억"))

patch_loss  = mpatches.Patch(color=C_PINK,  label="기회비용(손실)")
patch_gain  = mpatches.Patch(color=C_TEAL,  label="기회이득(초과이용)")
ax3.legend(handles=[patch_loss, patch_gain],
           fontsize=9, frameon=False, labelcolor=C_TEXT, loc="upper right")

# ────────────────────────────────────────────────────────────────
# Chart 4 · 수평 바 — 자치구별 건당 탄소 경제효율
# ────────────────────────────────────────────────────────────────
style_ax(ax4, "자치구별 건당 탄소 경제효율 (투자 우선순위)",
         "초록색 = 효율 상위 5개 자치구 (투자 1순위)")

bar_colors_h = [C_TEAL if v >= THRESHOLD else C_BLUE for v in gu_eff]
hbars = ax4.barh(gu_names, gu_eff, color=bar_colors_h,
                 edgecolor=[C_TEAL if v >= THRESHOLD else C_BLUE for v in gu_eff],
                 linewidth=1, height=0.65, zorder=3)

# 수치 라벨
for bar, val in zip(hbars, gu_eff):
    ax4.text(val + 0.04, bar.get_y() + bar.get_height() / 2,
             f"{val}원", va="center", ha="left",
             fontsize=9, color=C_TEXT)

# 기준선
ax4.axvline(THRESHOLD, color=C_ORANGE, linewidth=1.2,
            linestyle="--", alpha=0.7, label=f"상위권 기준 ({THRESHOLD}원)")
ax4.set_xlabel("건당 탄소경제효율 (원/건)", color=C_MUTED, fontsize=10)
ax4.set_xlim(0, 7.5)
ax4.tick_params(axis="y", labelsize=10, colors=C_TEXT)
ax4.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:.0f}원"))
ax4.grid(axis="x", color="#1e3040", linewidth=0.7, linestyle="--", alpha=0.8)
ax4.grid(axis="y", visible=False)

patch_top = mpatches.Patch(color=C_TEAL, label="투자 1순위 (상위 5개 자치구)")
patch_etc = mpatches.Patch(color=C_BLUE, label="일반")
ax4.legend(handles=[patch_top, patch_etc],
           fontsize=9, frameon=False, labelcolor=C_TEXT, loc="lower right")

# ── 저장 ────────────────────────────────────────────────────────
OUTPUT = "ttareungi_dashboard.png"
plt.savefig(OUTPUT, dpi=150, bbox_inches="tight",
            facecolor=C_BG, edgecolor="none")
plt.show()
print(f"\n✅ 저장 완료: {OUTPUT}")
