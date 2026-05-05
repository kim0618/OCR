import re

_PHONE_RE = re.compile(r'\(?0\d{1,2}\)?[-\s]?\d{3,4}[-\s]?\d{4}')
_PHONE_LABELED_RE = re.compile(r'(?:TEL|Tel|tel|전화(?:\s*번호)?)\s*[:;]?\s*([()0-9\)\-\s.]{8,24})', re.I)
_PHONE_ADMIN_NOISE_RE = re.compile(
    r'여신금융|협회|신고안내|포상금|고객센터|카드번호|승인번호|거래일시|전표|'
    r'가맹No|가맹점No|가맹점번호|TID|CAT|VANKEY',
    re.I,
)
_ADDR_START_RE = re.compile(
    r'(서울|서울시|경기|경기도|인천|인천시|부산|부산시|대구|대구시|광주|광주시|대전|대전시|울산|울산시|세종|세종시|강원|강원도|충북|충청북도|충남|충청남도|전북|전라북도|전남|전라남도|경북|경상북도|경남|경상남도|제주|제주도)'
)
_NEXT_LABEL_RE = re.compile(
    r'\s*(?:사업자(?:등록)?번호|등록번호|대표자?|성명|주소|TEL|Tel|tel|전화|'
    r'가맹점명|가맹점No|가맹점번호|승인번호|카드번호|거래일시)\s*[:;]?',
    re.I,
)
_FIELD_NOISE_RE = re.compile(
    r'단가수량|단가|수량|금액|합계|총계|subtotal|total|tax|cash|'
    r'품목|상품명|주문|테이블|단말|영수증|안내|정보|포털|결제|전표|승인|거래|'
    r'사업자번호|등록번호|가맹점명|가맹점번호|가맹점no|가맹점|상호|회사명|업체명|대표자|성명|주소|전화|tel|작성년월일|'
    r'업태|업종|도매|소매|중개업|서비스업|상품중개업|일반목적용기계및장비|'
    r'cashier|server|guests|station|order|table|dine\s*in|code|desc|qty|price|amount',
    re.I,
)
_REPRESENTATIVE_NOISE_RE = re.compile(
    r'테이블|단말|번호|영수증|번길|주문|품목|수량|단가|금액|주소|사업자|가맹점|상호|회사명|'
    r'cashier|server|guests|station|order|table|menu|item|qty|price|amount',
    re.I,
)
_REPRESENTATIVE_LABEL_ANCHOR_RE = re.compile(
    r'(?:대표자\s*명|대표자|대표(?!\w)|성\s*명|공급자\s*성\s*명|공급자\s*명|예금주명|예금주)',
    re.I,
)
_REPRESENTATIVE_COMPANYISH_RE = re.compile(
    r'(?:주식회사|\(주\)|상사|철물|조명|전기|공구|볼트|약국|카페|마트|편의점|스토어|매장|툴|'
    r'IBK|NH|KB|비씨|신한|국민|하나|우리|기업은행|cashnote|paykey|vankey)',
    re.I,
)
_COMPANY_SUFFIX_HINT_RE = re.compile(
    r'(\(주\)|주식회사|상사|철물|조명|전기|공구|볼트|약국|카페|마트|편의점|스토어|매장|집|점|GS25|CU|세븐일레븐|코리아)$',
    re.I,
)
_COMPANY_LABEL_RE = re.compile(
    r'(?:상호\s*명?|가맹점\s*명|회사\s*명|업체\s*명|매장\s*명|브랜드\s*명|상점\s*명|사업장\s*명|판매자|공급자)(?!\s*(?:성명|명|번호|주소))\s*[:;]?',
    re.I,
)
_COMPANY_CONTEXT_HINT_RE = re.compile(
    r'(?:상사|철물|조명|전기|공구|볼트|약국|카페|마트|편의점|스토어|매장|식당|상회|집|점|툴|주식회사|\(주\)|㈜)$',
    re.I,
)
_CONVENIENCE_STORE_NAME_RE = re.compile(r'^(?:GS25|CU|세븐일레븐|이마트24|미니스톱)[가-힣A-Za-z0-9()]*점$', re.I)
_COMPANY_SLOGAN_RE = re.compile(
    r'(?:함께|[가-힣]께)하는행복|응원합니다|감사합니다|포인트적립|행사문구|안내문구|'
    r'정부방침|교환|지참|가능합니다'
)
_PERSON_LIKE_NAME_RE = re.compile(r'^[가-힣]{3}$')
_REPRESENTATIVE_SURNAME_RE = re.compile(r'^[김이박최정강조윤장임한오서신권황안송전홍유고문양손배조백허남심노하곽성차주우구민류진나엄채원천방공현함변염여추도소석선설마길연위표명기반왕금옥육인맹제모장모국어은편용]')  # noqa: E501
_ADDRESS_CUT_RE = re.compile(
    r'\s*(?:TEL|Tel|tel|전화|FAX|fax|사업자(?:등록)?번호|등록번호|대표자?|성명|상호|회사명|업체명|가맹점명|'
    r'가맹No|가맹점No|가맹점번호|승인번호|카드번호|카드사|은행|매입사|거래일시|품목|상품명|수량|단가|금액|합계|총계|부가세|공급가액|'
    r'판매금액|봉사료|결제|전표|테이블명|판매시간|판매사원|영수번호|작성년월일|공급대가|도매|소매|업태|업종|안내|고객센터)\s*[:;]?',
    re.I,
)
_ADDRESS_LABEL_RE = re.compile(
    r'(?:사업장\s*)?(?:주소|소재지)|공급자\s*주소|업체\s*주소|본점\s*소재지|사업장\s*소재지',
    re.I,
)
_ADDRESS_CORE_TOKEN_RE = re.compile(r'시|도|군|구|읍|면|동|리|가|로|길|번길|층|호|번지')
_ADDRESS_STORE_NOISE_RE = re.compile(r'GS25|CU|세븐일레븐|편의점|카페|약국|마트|스토어|매장|점$', re.I)
_LABEL_ONLY_RE = re.compile(
    r'^(?:사업자|사업자번호|등록|등록번호|공급자|가맹점명|가맹점번호|가맹점no|가맹점|상호|회사명|업체명|대표자|성명|주소|전화|tel|작성년월일)$',
    re.I,
)
_ADDRESS_CONTINUATION_RE = re.compile(r'(?:[가-힣A-Za-z0-9(),.\-\s]*(?:로|길|번길|동|읍|면|리|가|층|호|번지|[A-Z]\s*동|제\s*\d+\s*호)[가-힣A-Za-z0-9(),.\-\s]*)')
_ADDRESS_BROAD_ONLY_RE = re.compile(r'^(?:서울|경기|경기도|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)\s+[가-힣]+시\s+[가-힣]+구$')
_ADDRESS_TRAILING_NOISE_RE = re.compile(
    r'\s*(?:대표자|성명|상호|회사명|업체명|사업자|등록번호|공급자|도매|소매|업태|업종|일반목적|배\s*관|전\s*기|작성년월일|공급대가|'
    r'테이블명|판매시간|판매사원|영수번호|카드종류|카드번호|카드사|은행|매입사|승인|전표|TID|CAT|VANKEY|IBK|비씨|체크|신용|'
    r'품목|상품명|수량|단가|금액|합계|총계|판매금액|봉사료|안내|고객센터|'
    r'(?<![-\d])\b\d{1,3}[,.]\d{3}(?:[,.]\d{3})?|제\d{1,2}[-\s]?\d{2,}|[*A-Z]{2,}\d*)',
    re.I,
)
