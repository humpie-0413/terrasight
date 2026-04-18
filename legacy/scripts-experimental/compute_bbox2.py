import math

# All counties in WGS84 (W, S, E, N)
all_counties = {
    # Buffalo-Cheektowaga NY (15380): Erie + Niagara
    '15380': [
        (-79.31, 42.44, -78.46, 43.39),  # Erie County NY
        (-79.11, 43.07, -78.47, 43.57),  # Niagara County NY
    ],
    # Richmond VA (40060): many counties + independent cities
    '40060': [
        (-77.99, 37.19, -77.25, 37.57),  # Chesterfield
        (-77.65, 37.49, -77.17, 37.74),  # Henrico
        (-77.52, 37.48, -77.30, 37.60),  # Richmond city
        (-77.47, 37.11, -77.02, 37.46),  # Prince George
        (-77.72, 37.09, -77.24, 37.52),  # Dinwiddie
        (-77.40, 37.22, -77.28, 37.31),  # Petersburg city
        (-77.39, 37.31, -77.33, 37.38),  # Colonial Heights
        (-77.24, 37.32, -77.16, 37.40),  # Hopewell
        (-77.67, 37.70, -77.07, 38.23),  # Hanover
        (-78.20, 37.24, -77.69, 37.60),  # Amelia
        (-77.19, 37.43, -76.65, 37.97),  # King and Queen
        (-77.35, 37.52, -76.78, 37.91),  # King William
        (-77.24, 37.38, -76.74, 37.63),  # New Kent
        (-78.13, 37.41, -77.66, 37.69),  # Powhatan
        (-77.62, 36.71, -76.95, 37.11),  # Sussex
        (-77.27, 37.22, -76.87, 37.49),  # Charles City
        (-78.16, 37.56, -77.62, 37.91),  # Goochland
    ],
    # Salt Lake City UT (41620): Salt Lake + Tooele
    '41620': [
        (-112.10, 40.27, -111.65, 40.97),  # Salt Lake County
        (-114.05, 39.54, -111.86, 41.08),  # Tooele County
    ],
    # Memphis TN-MS-AR (32820): Shelby TN, Fayette TN, Tipton TN, DeSoto MS, Crittenden AR, Benton MS, Marshall MS, Tate MS, Tunica MS
    '32820': [
        (-90.31, 35.00, -89.73, 35.48),  # Shelby County TN
        (-89.73, 35.00, -89.28, 35.48),  # Fayette County TN
        (-90.17, 35.20, -89.54, 35.55),  # Tipton County TN
        (-90.31, 34.72, -89.73, 35.00),  # DeSoto County MS
        (-90.49, 35.01, -90.04, 35.72),  # Crittenden County AR
        (-89.35, 34.58, -89.02, 35.00),  # Benton County MS
        (-89.72, 34.49, -89.25, 35.00),  # Marshall County MS
        (-90.24, 34.55, -89.67, 34.77),  # Tate County MS
        (-90.59, 34.42, -90.20, 34.89),  # Tunica County MS
    ],
    # Louisville KY-IN (31140): Jefferson KY, Clark IN, Floyd IN, Bullitt KY, Oldham KY, Harrison IN, Washington IN, Henry KY, Meade KY, Nelson KY, Shelby KY, Spencer KY
    '31140': [
        (-85.94, 38.02, -85.41, 38.37),  # Jefferson County KY
        (-85.95, 38.31, -85.42, 38.65),  # Clark County IN
        (-85.85, 38.19, -85.53, 38.43),  # Floyd County IN
        (-85.94, 37.81, -85.43, 38.12),  # Bullitt County KY
        (-85.64, 38.29, -85.28, 38.52),  # Oldham County KY
        (-86.33, 37.96, -85.90, 38.42),  # Harrison County IN
        (-86.31, 38.42, -85.85, 38.78),  # Washington County IN
        (-85.35, 38.34, -84.87, 38.60),  # Henry County KY
        (-86.49, 37.80, -85.98, 38.20),  # Meade County KY
        (-85.74, 37.52, -85.15, 37.99),  # Nelson County KY
        (-85.47, 38.09, -84.96, 38.36),  # Shelby County KY
        (-85.52, 37.94, -85.10, 38.15),  # Spencer County KY
    ],
    # Milwaukee WI (33340): Milwaukee, Waukesha, Ozaukee, Washington
    '33340': [
        (-88.07, 42.84, -87.75, 43.19),  # Milwaukee County
        (-88.41, 42.84, -88.05, 43.19),  # Waukesha County
        (-88.07, 43.19, -87.81, 43.54),  # Ozaukee County
        (-88.40, 43.19, -88.00, 43.55),  # Washington County
    ],
    # Oklahoma City OK (36420): Oklahoma, Canadian, Cleveland, Logan, Grady, Lincoln, McClain
    '36420': [
        (-97.67, 35.28, -97.08, 35.68),  # Oklahoma County
        (-98.45, 35.28, -97.67, 35.68),  # Canadian County
        (-97.67, 34.90, -97.09, 35.29),  # Cleveland County
        (-97.67, 35.68, -97.08, 36.27),  # Logan County
        (-98.11, 34.89, -97.67, 35.67),  # Grady County
        (-97.09, 35.36, -96.59, 35.89),  # Lincoln County
        (-97.67, 34.88, -97.08, 35.19),  # McClain County
    ],
    # Tucson AZ (46060): Pima only
    '46060': [
        (-113.33, 31.33, -110.45, 32.51),  # Pima County
    ],
    # Jacksonville FL (27260): Duval, Clay, Nassau, St. Johns, Baker
    '27260': [
        (-82.05, 30.12, -81.39, 30.59),  # Duval County
        (-82.05, 29.80, -81.49, 30.12),  # Clay County
        (-82.05, 30.58, -81.40, 31.01),  # Nassau County
        (-81.75, 29.78, -81.18, 30.13),  # St. Johns County
        (-82.47, 30.12, -82.05, 30.59),  # Baker County
    ],
    # Birmingham AL (13820): Jefferson, Shelby, Bibb, Blount, St. Clair, Walker
    '13820': [
        (-87.30, 33.46, -86.51, 33.92),  # Jefferson County
        (-87.06, 33.22, -86.35, 33.60),  # Shelby County
        (-87.42, 32.97, -86.90, 33.38),  # Bibb County
        (-86.90, 33.97, -86.29, 34.46),  # Blount County
        (-86.54, 33.69, -86.03, 34.24),  # St. Clair County
        (-87.66, 33.77, -87.04, 34.10),  # Walker County
    ],
}

margin = 0.2
print("CBSA Bounding Boxes (+0.2 deg margin):")
for cbsa, counties in all_counties.items():
    Ws = [c[0] for c in counties]
    Ss = [c[1] for c in counties]
    Es = [c[2] for c in counties]
    Ns = [c[3] for c in counties]
    W = round(min(Ws) - margin, 2)
    S = round(min(Ss) - margin, 2)
    E = round(max(Es) + margin, 2)
    N = round(max(Ns) + margin, 2)
    print(f"CBSA {cbsa}: west={W}, south={S}, east={E}, north={N}")
