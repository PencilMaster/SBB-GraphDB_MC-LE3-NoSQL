import pandas as pd


import pandas as pd

def valid_ids(  comp1: pd.DataFrame, 
                comp2: pd.DataFrame
                ) -> tuple[pd.DataFrame, pd.DataFrame]:
    if "rHaltestelle" not in comp1.columns or not {"xtf_id", "Name"}.issubset(comp2.columns): 
        raise ValueError("Missing 'rHaltestelle', 'xtf_id', or 'Name' column.")
    
    comp2 = comp2[comp2["Betriebspunkttyp_Bezeichnung"] == "Haltestelle"]
    common_ids = set(comp1["rHaltestelle"]).intersection(comp2["xtf_id"])

    # Isolate the filtered views and force copies to prevent SettingWithCopyWarning
    comp1_filtered = comp1[comp1["rHaltestelle"].isin(common_ids)].copy()
    comp2_filtered = comp2[comp2["xtf_id"].isin(common_ids)]

    # Vectorized hash map lookup to emulate an inner join
    name_mapping = comp2_filtered.set_index("xtf_id")["Name"]
    comp1_filtered["Name"] = comp1_filtered["rHaltestelle"].map(name_mapping)

    # Filter out stops with the same name, that KNN will be better.
    comp1_filtered = comp1_filtered.drop_duplicates(subset=["Name"])

    return comp1_filtered, comp2_filtered
    

def create_clean_ids(   comp1: str, 
                        comp2: str
                        ):
    base_path = "../data/"
    
    df_table1 =     pd.read_csv(base_path + comp1, low_memory=False)
    df_table2 =     pd.read_csv(base_path + comp2, low_memory=False)

    df_table1_clean, df_table2_clean = valid_ids(df_table1, df_table2)
    
    pd.DataFrame.to_csv(df_table1_clean,    "../data/df_haltekante_clean.csv")
    # pd.DataFrame.to_csv(df_table2_clean,    "../data/df_betriebspunkt_clean.csv")
    return
    

if __name__ == "__main__":
    create_clean_ids("Haltekante.csv", "Betriebspunkt.csv")