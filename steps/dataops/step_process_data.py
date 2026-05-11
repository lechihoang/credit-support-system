from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("dataops.process")

BANKING77_LABELS = dict(
    enumerate(
        [
            "activate_my_card",
            "age_limit",
            "apple_pay_or_google_pay",
            "atm_support",
            "automatic_top_up",
            "balance_not_updated_after_bank_transfer",
            "balance_not_updated_after_cheque_or_cash_deposit",
            "beneficiary_not_allowed",
            "cancel_transfer",
            "card_about_to_expire",
            "card_acceptance",
            "card_arrival",
            "card_delivery_estimate",
            "card_linking",
            "card_not_working",
            "card_payment_fee_charged",
            "card_payment_not_recognised",
            "card_payment_wrong_exchange_rate",
            "card_swallowed",
            "cash_withdrawal_charge",
            "cash_withdrawal_not_recognised",
            "change_pin",
            "compromised_card",
            "contactless_not_working",
            "country_support",
            "declined_card_payment",
            "declined_cash_withdrawal",
            "declined_transfer",
            "direct_debit_payment_not_recognised",
            "disposable_card_limits",
            "edit_personal_details",
            "exchange_charge",
            "exchange_rate",
            "exchange_via_app",
            "extra_charge_on_statement",
            "failed_transfer",
            "fiat_currency_support",
            "get_disposable_virtual_card",
            "get_physical_card",
            "getting_spare_card",
            "getting_virtual_card",
            "lost_or_stolen_card",
            "lost_or_stolen_phone",
            "order_physical_card",
            "passcode_forgotten",
            "pending_card_payment",
            "pending_cash_withdrawal",
            "pending_top_up",
            "pending_transfer",
            "pin_blocked",
            "receiving_money",
            "refund_not_showing_up",
            "request_refund",
            "reverted_card_payment",
            "supported_cards_and_currencies",
            "terminate_account",
            "top_up_by_bank_transfer_charge",
            "top_up_by_card_charge",
            "top_up_by_cash_or_cheque",
            "top_up_failed",
            "top_up_limits",
            "top_up_reverted",
            "topping_up_by_card",
            "transaction_charged_twice",
            "transfer_fee_charged",
            "transfer_into_account",
            "transfer_not_received_by_recipient",
            "transfer_timing",
            "unable_to_verify_identity",
            "verify_my_identity",
            "verify_source_of_funds",
            "verify_top_up",
            "virtual_card_not_working",
            "visa_or_mastercard",
            "why_verify_identity",
            "wrong_amount_of_cash_received",
            "wrong_exchange_rate_for_cash_withdrawal",
        ]
    )
)

INTENT_TO_4CLASS = {
    "card_payment_not_recognised": "Fraud",
    "cash_withdrawal_not_recognised": "Fraud",
    "compromised_card": "Fraud",
    "direct_debit_payment_not_recognised": "Fraud",
    "lost_or_stolen_card": "Fraud",
    "lost_or_stolen_phone": "Fraud",
    "card_about_to_expire": "Card Lock",
    "card_linking": "Card Lock",
    "change_pin": "Card Lock",
    "pin_blocked": "Card Lock",
    "terminate_account": "Card Lock",
    "atm_support": "Balance Inquiry",
    "automatic_top_up": "Balance Inquiry",
    "balance_not_updated_after_bank_transfer": "Balance Inquiry",
    "balance_not_updated_after_cheque_or_cash_deposit": "Balance Inquiry",
    "beneficiary_not_allowed": "Balance Inquiry",
    "cancel_transfer": "Balance Inquiry",
    "cash_withdrawal_charge": "Balance Inquiry",
    "declined_cash_withdrawal": "Balance Inquiry",
    "declined_transfer": "Balance Inquiry",
    "extra_charge_on_statement": "Balance Inquiry",
    "failed_transfer": "Balance Inquiry",
    "pending_card_payment": "Balance Inquiry",
    "pending_cash_withdrawal": "Balance Inquiry",
    "pending_top_up": "Balance Inquiry",
    "pending_transfer": "Balance Inquiry",
    "receiving_money": "Balance Inquiry",
    "refund_not_showing_up": "Balance Inquiry",
    "request_refund": "Balance Inquiry",
    "reverted_card_payment": "Balance Inquiry",
    "top_up_by_bank_transfer_charge": "Balance Inquiry",
    "top_up_by_card_charge": "Balance Inquiry",
    "top_up_by_cash_or_cheque": "Balance Inquiry",
    "top_up_failed": "Balance Inquiry",
    "top_up_limits": "Balance Inquiry",
    "top_up_reverted": "Balance Inquiry",
    "transfer_fee_charged": "Balance Inquiry",
    "transfer_into_account": "Balance Inquiry",
    "transfer_not_received_by_recipient": "Balance Inquiry",
    "transfer_timing": "Balance Inquiry",
    "verify_source_of_funds": "Balance Inquiry",
    "verify_top_up": "Balance Inquiry",
    "wrong_amount_of_cash_received": "Balance Inquiry",
    "wrong_exchange_rate_for_cash_withdrawal": "Balance Inquiry",
    "activate_my_card": "Complaint",
    "age_limit": "Complaint",
    "apple_pay_or_google_pay": "Complaint",
    "card_acceptance": "Complaint",
    "card_arrival": "Complaint",
    "card_delivery_estimate": "Complaint",
    "card_not_working": "Complaint",
    "card_payment_fee_charged": "Complaint",
    "card_payment_wrong_exchange_rate": "Complaint",
    "card_swallowed": "Complaint",
    "contactless_not_working": "Complaint",
    "country_support": "Complaint",
    "declined_card_payment": "Complaint",
    "disposable_card_limits": "Complaint",
    "edit_personal_details": "Complaint",
    "exchange_charge": "Complaint",
    "exchange_rate": "Complaint",
    "exchange_via_app": "Complaint",
    "fiat_currency_support": "Complaint",
    "get_disposable_virtual_card": "Complaint",
    "get_physical_card": "Complaint",
    "getting_spare_card": "Complaint",
    "getting_virtual_card": "Complaint",
    "order_physical_card": "Complaint",
    "passcode_forgotten": "Complaint",
    "supported_cards_and_currencies": "Complaint",
    "topping_up_by_card": "Complaint",
    "transaction_charged_twice": "Complaint",
    "unable_to_verify_identity": "Complaint",
    "verify_my_identity": "Complaint",
    "virtual_card_not_working": "Complaint",
    "visa_or_mastercard": "Complaint",
    "why_verify_identity": "Complaint",
}


def map_dataset(input_csv: Path) -> pd.DataFrame:
    logger.info("Mapping dataset from %s", input_csv)
    df = pd.read_csv(input_csv)
    if "label" in df.columns:
        df["intent"] = df["label"].map(BANKING77_LABELS)
        df["simplified"] = df["intent"].map(INTENT_TO_4CLASS)
    elif "category" in df.columns:
        df["intent"] = df["category"]
        df["simplified"] = df["category"].map(INTENT_TO_4CLASS)
    else:
        raise KeyError("Missing 'label' or 'category' column")
    out = df[["text", "intent", "simplified"]]
    logger.info("Mapped dataset from %s with %d rows", input_csv, len(out))
    return out


def to_mltable(df: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "data.parquet", index=False)
    (out_dir / "MLTable").write_text(
        "type: mltable\npaths:\n  - file: ./data.parquet\ntransformations:\n  - read_parquet: {}\n",
        encoding="utf-8",
    )
    logger.info("Wrote MLTable to %s with %d rows", out_dir, len(df))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-mlops", required=True)
    parser.add_argument("--processed-mlops", required=True)
    args = parser.parse_args()

    raw_mlops = Path(args.raw_mlops)
    processed_mlops = Path(args.processed_mlops)
    logger.info("Starting data processing. Raw %s, processed %s", raw_mlops, processed_mlops)

    train_df = map_dataset(raw_mlops / "train_raw.csv")
    test_df = map_dataset(raw_mlops / "test_raw.csv")

    to_mltable(train_df, processed_mlops / "train_data_mltable")
    to_mltable(test_df, processed_mlops / "test_data_mltable")
    logger.info("Step completed")


if __name__ == "__main__":
    main()
