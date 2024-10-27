import os
import json


from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
import requests
from openai import OpenAI


load_dotenv()

USER_NAME = "MaksymBratsiun"
REPO = "FM_Sentinel-2"

app = FastAPI()

GITHUB_API_URL = "https://api.github.com"


@app.get("/analyze_repo")
async def analyze_repo(target_url: str, branch: str = "main"):

    contents_url = f"{GITHUB_API_URL}/repos/{USER_NAME}/{REPO}/contents"
    response = requests.get(contents_url, params={"ref": branch})

    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Repository not found or could not be accessed")

    files_data = response.json()
    files_to_analyze = {}

    def read_files(files):
        for file_info in files:
            if file_info['type'] == 'file':
                if file_info['name'].endswith((".py", ".md", ".ini")):
                    file_response = requests.get(file_info['download_url'])
                    if file_response.status_code == 200:
                        files_to_analyze.update({file_info['path']: file_response.text})
                else:
                    files_to_analyze.update({file_info['path']: None})
            elif file_info['type'] == 'dir':
                subdir_response = requests.get(file_info['_links']['self'])
                if subdir_response.status_code == 200:
                    read_files(subdir_response.json())

    read_files(files_data)
    with open("data.json", "w", encoding='utf-8', errors="ignore") as file:
        json.dump(files_to_analyze, file)
    return list(files_to_analyze)


@app.get("/open_api_test")
def open_api_test():

    dev_level = "junior"
    project_structure = [".gitignore",
                         "FM_Sentenel-2.ipynb",
                         "README.md",
                         "Report about Test Task_Internship.pdf",
                         "figure_matching.py",
                         "img_2.png",
                         "img_3.png",
                         "pyproject.toml",
                         "requirements.txt",
                         "test_data/S2A_MSIL1C_20180611T083601_N0206_R064_T36UYA_20180611T104008.SAFE.txt",
                         "test_data/S2A_MSIL1C_20180611T083601_N0206_R064_T37UCR_20180611T104008.SAFE.txt",
                         "test_data/gomil_winter.JPG",
                         "test_data/gomil_winter_1.jpg",
                         "test_data/gomil_winter_2.jpg",
                         "test_data/gomil_winter_rot.JPG",
                         "test_data/gomil_winter_rot_sc.jpg"]
    files_to_analyze = {("README.md",
                         "# FM_Sentinel-2\n\n# Task\n\nComputer vision.\n\nSentinel-2 image matching In this task, you will work on the algorithm (or model) for matching satellite images. \nFor the dataset creation, you can download Sentinel-2 images from the official source here or use our dataset from Kaggle. \nYour algorithm should work with images from different seasons. \n\nFor this purpose you need: \n- Prepare a dataset for keypoints detection and image matching (in case of using the ML approach). \n- Build / train the algorithm.\n- Prepare demo code / notebook of the inference results. \n\nThe output for this task should contain: \n- Jupyter notebook that explains the process of the dataset creation. \n-  Link to the dataset (Google Drive, etc.).\n- Link to model weights. \n- Python script (.py) for model training or algorithm creation. \n- Python script (.py) for model inference. \n- Jupyter notebook with demo should have the functionality for observing detected keypoints and their matches:\n\n![img_3.png](img_3.png)\n\n Recommendation: \n- Classical solutions can be not accurate enough for images from different seasons. \n- Satellite images have large sizes. \nYou should think about how to process them in order not to lose the quality. \n- Some initial knowledge about satellite imagery processing you can find here.\n\n# Overview\nThis repository contains Python scripts for figure matching. Input needs 2 images like Sentinel-2 images with 1 chanel. \nScript search potential keypoints locations and calculate distance between them. Its match via algorithm SIFT \n(optionally we can use ORB), compare images and insert lines between keypoints and save results. \nThere are test data for test matching and demonstration. \n\n# Requirements\n- Python 3.x\n- OpenCV-python\n- Other dependencies (install using `pip install -r requirements.txt`)\n\n# Usage\n- update project from Git\n- create virtual environment\n\n```bash\npip install -r requirements.txt\n```\nLoad from link datasets\n```\nS2A_MSIL1C_20180611T083601_N0206_R064_T36UYA_20180611T104008.SAFE\nhttps://zipper.dataspace.copernicus.eu/odata/v1/Products(48e6b7ad-83f1-5a96-9b92-5be7952e99dc)/$value\nhttps://drive.google.com/drive/folders/11Zxi356GqXAzCSZew2_uhLGQzaO8oiQk\n```\n```\nS2A_MSIL1C_20180611T083601_N0206_R064_T37UCR_20180611T104008.SAFE\nhttps://zipper.dataspace.copernicus.eu/odata/v1/Products(01936382-06f4-587c-b000-9974e7c798e1)/$value\nhttps://drive.google.com/drive/folders/1peqWGOMMNJ135B4o9hzpCpwzrYrZhdp2\n```\n\nSet path to images and number of matches in script `figure_matching.py`\n```\nPATH_1 = \"..._B8A.jp2\"\nPATH_2 = \"..._B8A.jp2\"\nMATCHES = 20\n```\n\nRun `figure_matching.py`:\n```bash\npython  figure_matching.py\n```\nWatch result in `output_image.jpg`:\n\n![img_2.png](img_2.png)\n\n# Conclusion\n\nChoose SIFT because it better with different light gradient. \nUse `B8A` chanel because it was more stable and did not depend on the season and small size and good resolution.\n\nOther channels:\n\n    B1 60 m 443 nm Ultra Blue (coastal and aerosol)\n    B2 10 m 490 nm Blue\n    B3 10 m 560 nm Green\n    B4 10 m 665 nm Red\n    B5 20 m 705 nm Visible and near infrared (VNIR)\n    B6 20 m 740 nm Visible and near infrared (VNIR)\n    B7 20 m 783 nm Visible and near infrared (VNIR)\n    B8 10 m 842 nm Visible and near infrared (VNIR)\n    B8A 20 m 865 nm Visible and near infrared (VNIR)\n    B9 60 m 940 nm Short Wave Infrared (SWIR)\n    B10 60 m 1375 nm Short Wave Infrared (SWIR)\n    B11 20 m 1610 nm Short Wave Infrared (SWIR)\n    B12 20 m 2190 nm Short Wave Infrared (SWIR)\n    TCI 10 m 490, 560, 665 nm True Color Image (BGR) \n\nSave without compressing for easy validation. Draw first 20 matches.\n"),
                        ("figure_matching.py",
                         r"import cv2\n\n# Change PATH_1, PATH_2, MATCHES according your purpose\nPATH_1 = \"test_data/S2A_MSIL1C_20180611T083601_N0206_R064_T36UYA_20180611T104008.SAFE/GRANULE/L1C_T36UYA_A015505_\\\n20180611T084243/IMG_DATA/T36UYA_20180611T083601_B8A.jp2\"\nPATH_2 = \"test_data/S2A_MSIL1C_20180611T083601_N0206_R064_T37UCR_20180611T104008.SAFE/GRANULE/L1C_T37UCR_A015505_\\\n20180611T084243/IMG_DATA/T37UCR_20180611T083601_B8A.jp2\"\nMATCHES = 20\n\nif __name__ == '__main__':\n    img1 = cv2.imread(PATH_1, cv2.IMREAD_GRAYSCALE)\n    img2 = cv2.imread(PATH_2, cv2.IMREAD_GRAYSCALE)\n\n    sift = cv2.SIFT_create()\n    kp1, des1 = sift.detectAndCompute(img1, None)\n    kp2, des2 = sift.detectAndCompute(img2, None)\n    bf = cv2.BFMatcher()\n    matches = bf.knnMatch(des1, des2, k=2)\n    matches = sorted(matches, key=lambda x: x[0].distance)\n    good = []\n    for m, n in matches:\n        if m.distance < 0.75 * n.distance:\n            good.append([m])\n    img3 = cv2.drawMatchesKnn(img1, kp1, img2, kp2, good[:MATCHES], None, flags=2)\n\n    for match in good[:MATCHES]:\n        m = match[0]\n        pt1 = (int(kp1[m.queryIdx].pt[0]), int(kp1[m.queryIdx].pt[1]))\n        pt2 = (int(kp2[m.trainIdx].pt[0] + img1.shape[1]), int(kp2[m.trainIdx].pt[1]))\n        img3 = cv2.line(img3, pt1, pt2, (0, 255, 0), 2)\n    cv2.imwrite('output_image.jpg', img3)\n")}

    analysis_results = []
    result = []
    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'), )
    grade = "junior"

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": f"You are an experienced software reviewer, specialized in assessing code quality. "
                            f"Analyze the structure of the following project"
                 },
                {"role": "user",
                 "content": (f"{project_structure}"
                             f"Downsides: identifying weaknesses and issues."
                             f"Comments: write a summary conclusion about structure."
                             )}
            ],
            max_tokens=500,
            temperature=0.8
        )
        analysis_results.append({"analysis": response.choices})
    except Exception as e:
        analysis_results.append({"error": str(e)})
    print(analysis_results)
    for file_name, file_content in files_to_analyze:
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system",
                     "content": f"You are an experienced software reviewer"
                                f"This code wrote by {dev_level} level developer. "
                                f"Evaluate the code, identifying weaknesses and issues, and give feedback. "
                     },
                    {"role": "user",
                     "content": (f"Fale name: '{file_name}'"
                                 f"{file_content}"
                                 f"Downsides: identifying weaknesses and issues."
                                 f"Comments: write a brief comment on the developer’s skills."
                                 )}
                ],
                max_tokens=500,
                temperature=0.8
            )
            analysis_results.append({"analysis": response.choices})
        except Exception as e:
            analysis_results.append({"error": str(e)})
    print(analysis_results)
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": f"You are an experienced software reviewer, specialized in assessing code quality. "
                            f"Based on the analysis, summarize the project"
                 },
                {"role": "user",
                 "content": (f"{analysis_results}"
                             f"Downsides: identifying weaknesses and issues."
                             f"Comments: write a summary conclusion."
                             f"Please evaluate the code as a {dev_level}-level submission rate it on a scale of 1 to 5,"
                             f"like:'Rating 3/5 (for {dev_level} level)' in the line. "
                             )}
            ],
            max_tokens=500,
            temperature=0.8
        )
        result.append({"analysis": response.choices})
    except Exception as e:
        result.append({"error": str(e)})
    analysis_results.extend(result)
    print(analysis_results)
    return result
