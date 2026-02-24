# ComfyUI GFPGAN

This is a custom node for [ComfyUI](https://github.com/comfyanonymous/ComfyUI) that enables face restoration using [GFPGAN](https://github.com/TencentARC/GFPGAN).

## Installation

1.  **Navigate to the Custom Nodes Directory**  
    ```bash
    cd /path/to/your/ComfyUI/custom_nodes/
    ```

2.  **Clone the Repository**
    ```bash
    git clone https://github.com/lucak5s/comfyui_gfpgan.git
    ```

3. **Enter the Cloned Directory**  
    ```bash
    cd comfyui_gfpgan
    ```

4.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt && pip install gfpgan --no-deps
    ```
    > **Note:** We use `pip install gfpgan --no-deps` to avoid installing `gfpgan`’s default dependency on the outdated `basicsr` package, which is incompatible with newer versions of PyTorch. Make sure you have `stablesr-fixed` installed in your environment instead of `stablesr`.


## Usage

Start ComfyUI and look for the node named **"GFPGAN Face Restore."**  
The required face detection and face restoration models will be downloaded automatically and placed in the following directories:

- `ComfyUI/models/face_detection`  
- `ComfyUI/models/face_restoration`
