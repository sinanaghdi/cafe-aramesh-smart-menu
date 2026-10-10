from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Cafe, CafeTable, Category, Product, ProductTag, StudyModeRule

CAFE_NAME = "کافه آرامش"
CAFE_SLUG = "cafe-aramesh"

CATEGORIES = [
    ("hot-coffee", "قهوه گرم", 1),
    ("cold-drinks", "نوشیدنی سرد", 2),
    ("tea-and-infusion", "چای و دمنوش", 3),
    ("non-coffee", "نوشیدنی بدون قهوه", 4),
    ("food-and-dessert", "غذا و شیرینی", 5),
]

# Prices and margins are illustrative development data, expressed in toman (IRT).
PRODUCTS = [
    ("espresso", "hot-coffee", "اسپرسو", "قهوه غلیظ و کوتاه با عصاره‌گیری تازه.", 85000, 42000, {"temperature": ["hot"], "taste": ["bitter"], "caffeine": ["high"], "milk": ["no"], "strength": ["high"], "meal_type": ["any"], "allergen": ["none"]}),
    ("double-espresso", "hot-coffee", "اسپرسو دوبل", "دو شات اسپرسو برای شروعی پرقدرت.", 115000, 57000, {"temperature": ["hot"], "taste": ["bitter"], "caffeine": ["high"], "milk": ["no"], "strength": ["high"], "meal_type": ["morning"], "allergen": ["none"]}),
    ("americano", "hot-coffee", "آمریکانو", "اسپرسو با آب داغ؛ ساده و متعادل.", 105000, 52000, {"temperature": ["hot"], "taste": ["bitter"], "caffeine": ["high"], "milk": ["no"], "strength": ["medium"], "meal_type": ["any"], "allergen": ["none"]}),
    ("cappuccino", "hot-coffee", "کاپوچینو", "اسپرسو با شیر بخارداده‌شده و فوم لطیف.", 145000, 65000, {"temperature": ["hot"], "taste": ["creamy"], "caffeine": ["medium"], "milk": ["yes"], "strength": ["medium"], "meal_type": ["any"], "allergen": ["milk"]}),
    ("latte", "hot-coffee", "لاته", "قهوه متعادل با بافت نرم شیر.", 155000, 70000, {"temperature": ["hot"], "taste": ["creamy", "sweet"], "caffeine": ["medium"], "milk": ["yes"], "strength": ["low"], "meal_type": ["any"], "allergen": ["milk"]}),
    ("flat-white", "hot-coffee", "فلت وایت", "اسپرسو با شیر میکروفوم و طعم قهوه پررنگ.", 160000, 73000, {"temperature": ["hot"], "taste": ["creamy", "bitter"], "caffeine": ["high"], "milk": ["yes"], "strength": ["high"], "meal_type": ["morning"], "allergen": ["milk"]}),
    ("mocha", "hot-coffee", "موکا", "ترکیب اسپرسو، شکلات و شیر.", 175000, 79000, {"temperature": ["hot"], "taste": ["sweet", "creamy"], "caffeine": ["medium"], "milk": ["yes"], "strength": ["medium"], "meal_type": ["any"], "allergen": ["milk"]}),
    ("caramel-macchiato", "hot-coffee", "کارامل ماکیاتو", "اسپرسو، شیر و طعم کارامل.", 180000, 82000, {"temperature": ["hot"], "taste": ["sweet", "creamy"], "caffeine": ["medium"], "milk": ["yes"], "strength": ["medium"], "meal_type": ["any"], "allergen": ["milk"]}),
    ("filter-coffee", "hot-coffee", "قهوه دمی", "قهوه دمی با عطر روشن و طعم شفاف.", 135000, 60000, {"temperature": ["hot"], "taste": ["fruity", "bitter"], "caffeine": ["high"], "milk": ["no"], "strength": ["medium"], "meal_type": ["morning"], "allergen": ["none"]}),
    ("cold-brew", "cold-drinks", "کولد برو", "قهوه دم‌سرد با طعمی نرم و خنک.", 165000, 76000, {"temperature": ["cold", "iced"], "taste": ["bitter"], "caffeine": ["high"], "milk": ["no"], "strength": ["high"], "meal_type": ["any"], "allergen": ["none"]}),
    ("iced-americano", "cold-drinks", "آیس آمریکانو", "اسپرسو و آب خنک روی یخ.", 115000, 53000, {"temperature": ["cold", "iced"], "taste": ["bitter"], "caffeine": ["high"], "milk": ["no"], "strength": ["medium"], "meal_type": ["any"], "allergen": ["none"]}),
    ("iced-latte", "cold-drinks", "آیس لاته", "لاته خنک با شیر و یخ.", 165000, 74000, {"temperature": ["cold", "iced"], "taste": ["creamy", "sweet"], "caffeine": ["medium"], "milk": ["yes"], "strength": ["low"], "meal_type": ["any"], "allergen": ["milk"]}),
    ("affogato", "food-and-dessert", "آفوگاتو", "اسپرسوی داغ روی بستنی وانیلی.", 175000, 80000, {"temperature": ["hot", "cold"], "taste": ["sweet", "creamy", "bitter"], "caffeine": ["medium"], "milk": ["yes"], "strength": ["medium"], "meal_type": ["dessert"], "allergen": ["milk"]}),
    ("lemonade", "non-coffee", "لیموناد", "نوشیدنی خنک با لیموی تازه.", 125000, 60000, {"temperature": ["cold", "iced"], "taste": ["sour", "sweet"], "caffeine": ["none"], "milk": ["no"], "strength": ["low"], "meal_type": ["any"], "allergen": ["none"]}),
    ("sour-cherry-lemonade", "non-coffee", "لیموناد آلبالو", "ترشی لیمو در کنار عطر و طعم آلبالو.", 145000, 68000, {"temperature": ["cold", "iced"], "taste": ["sour", "fruity"], "caffeine": ["none"], "milk": ["no"], "strength": ["low"], "meal_type": ["any"], "allergen": ["none"]}),
    ("iced-hibiscus", "non-coffee", "چای ترش سرد", "دمنوش چای ترش با سرو خنک.", 120000, 56000, {"temperature": ["cold", "iced"], "taste": ["sour", "fruity"], "caffeine": ["none"], "milk": ["no"], "strength": ["low"], "meal_type": ["any"], "allergen": ["none"]}),
    ("matcha-latte", "non-coffee", "ماچا لاته", "ماچا با شیر و بافتی لطیف.", 190000, 90000, {"temperature": ["hot"], "taste": ["creamy", "bitter"], "caffeine": ["medium"], "milk": ["yes"], "strength": ["medium"], "meal_type": ["morning"], "allergen": ["milk"]}),
    ("black-tea", "tea-and-infusion", "چای سیاه", "چای سیاه خوش‌عطر و تازه‌دم.", 65000, 28000, {"temperature": ["hot"], "taste": ["bitter"], "caffeine": ["medium"], "milk": ["no"], "strength": ["medium"], "meal_type": ["any"], "allergen": ["none"]}),
    ("saffron-tea", "tea-and-infusion", "چای زعفران", "چای معطر با زعفران.", 95000, 43000, {"temperature": ["hot"], "taste": ["floral", "sweet"], "caffeine": ["medium"], "milk": ["no"], "strength": ["low"], "meal_type": ["any"], "allergen": ["none"]}),
    ("chamomile", "tea-and-infusion", "دمنوش بابونه", "دمنوش گیاهی با عطر ملایم.", 100000, 45000, {"temperature": ["hot"], "taste": ["floral"], "caffeine": ["none"], "milk": ["no"], "strength": ["low"], "meal_type": ["evening"], "allergen": ["none"]}),
    ("hot-chocolate", "non-coffee", "هات‌چاکلت", "شکلات داغ با شیر.", 150000, 65000, {"temperature": ["hot"], "taste": ["sweet", "creamy"], "caffeine": ["low"], "milk": ["yes"], "strength": ["low"], "meal_type": ["evening"], "allergen": ["milk"]}),
    ("croissant", "food-and-dessert", "کروسان کره‌ای", "کروسان تازه با لایه‌های ترد و کره‌ای.", 110000, 50000, {"temperature": ["room"], "taste": ["creamy"], "caffeine": ["none"], "milk": ["yes"], "strength": ["low"], "meal_type": ["breakfast"], "allergen": ["gluten", "milk"]}),
    ("cheesecake", "food-and-dessert", "چیزکیک", "چیزکیک خامه‌ای با پایه بیسکویتی.", 175000, 78000, {"temperature": ["cold"], "taste": ["sweet", "creamy"], "caffeine": ["none"], "milk": ["yes"], "strength": ["low"], "meal_type": ["dessert"], "allergen": ["gluten", "milk"]}),
    ("avocado-toast", "food-and-dessert", "تست آووکادو", "نان تست با آووکادو و چاشنی تازه.", 230000, 100000, {"temperature": ["hot"], "taste": ["creamy", "sour"], "caffeine": ["none"], "milk": ["no"], "strength": ["medium"], "meal_type": ["breakfast"], "allergen": ["gluten"]}),
    ("grilled-cheese-sandwich", "food-and-dessert", "ساندویچ پنیر گریل", "ساندویچ گرم با پنیر ذوب‌شده.", 210000, 92000, {"temperature": ["hot"], "taste": ["creamy", "savory"], "caffeine": ["none"], "milk": ["yes"], "strength": ["medium"], "meal_type": ["lunch"], "allergen": ["gluten", "milk"]}),
]


def seed() -> None:
    with SessionLocal() as session:
        with session.begin():
            cafe = session.scalar(select(Cafe).where(Cafe.slug == CAFE_SLUG))
            if cafe is None:
                cafe = Cafe(name=CAFE_NAME, slug=CAFE_SLUG, currency_unit="IRT", timezone="Asia/Tehran")
                session.add(cafe)
                session.flush()

            category_map: dict[str, Category] = {}
            for slug, name, sort_order in CATEGORIES:
                category = session.scalar(
                    select(Category).where(Category.cafe_id == cafe.id, Category.slug == slug)
                )
                if category is None:
                    category = Category(
                        cafe_id=cafe.id, name=name, slug=slug, sort_order=sort_order, is_active=True
                    )
                    session.add(category)
                else:
                    category.name = name
                    category.sort_order = sort_order
                    category.is_active = True
                category_map[slug] = category
            session.flush()

            for number in range(1, 9):
                table = session.scalar(
                    select(CafeTable).where(
                        CafeTable.cafe_id == cafe.id, CafeTable.table_number == number
                    )
                )
                if table is None:
                    session.add(CafeTable(
                        cafe_id=cafe.id,
                        table_number=number,
                        label=f"میز {number}",
                        qr_token=f"dev-demo-table-{number}-rotate-before-production",
                        is_active=True,
                    ))

            for slug, category_slug, name, description, price, margin, tags in PRODUCTS:
                product = session.scalar(
                    select(Product).where(Product.cafe_id == cafe.id, Product.slug == slug)
                )
                if product is None:
                    product = Product(cafe_id=cafe.id, slug=slug, name=name)
                    session.add(product)
                    session.flush()
                product.category_id = category_map[category_slug].id
                product.name = name
                product.description = description
                product.price_amount = price
                product.margin_amount = margin
                product.is_available = True
                product.is_featured = slug in {"cappuccino", "cold-brew", "sour-cherry-lemonade"}
                session.flush()

                old_tags = session.scalars(
                    select(ProductTag).where(ProductTag.product_id == product.id)
                ).all()
                for old_tag in old_tags:
                    session.delete(old_tag)
                session.flush()
                for tag_key, tag_values in tags.items():
                    for tag_value in tag_values:
                        session.add(ProductTag(
                            cafe_id=cafe.id,
                            product_id=product.id,
                            tag_key=tag_key,
                            tag_value=tag_value,
                        ))

            rule = session.scalar(select(StudyModeRule).where(StudyModeRule.cafe_id == cafe.id))
            if rule is None:
                session.add(StudyModeRule(
                    cafe_id=cafe.id,
                    enabled=False,
                    minimum_order_amount=200000,
                    allowed_durations_minutes=[120, 180],
                    allowed_start_time="08:00",
                    allowed_end_time="22:00",
                    max_concurrent_sessions=8,
                ))

    print(f"Seeded {CAFE_SLUG}: {len(PRODUCTS)} products and 8 sample tables.")


if __name__ == "__main__":
    seed()
