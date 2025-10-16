"""
颜色映射模块 - 管理颜色分类和索引
"""

class ColorMapper:
    def __init__(self):
        # 13个分类的颜色数据
        self.color_palette = {
            1: ["#051616", "#414545", "#808282", "#BEBFBF", "#FEFFFF", "#F9F6E9"],
            2: ["#CF354D", "#EE6F72", "#A6263D", "#F5ACA6", "#C98483", "#A35D5E", 
                "#69313B", "#E7D5D5", "#C0ACAB", "#755E5E"],
            3: ["#E95E2B", "#F98358", "#AB4226", "#FEBA9F", "#D9937C", "#AF6C58", 
                "#753B31", "#E9D5D0", "#C1ACA6", "#755E59"],
            4: ["#F49E16", "#FEAE3B", "#B16F16", "#FECE92", "#DAA76D", "#B3814B", 
                "#795126", "#F5E4CE", "#CDBCA9", "#806F5E"],
            5: ["#EDCA16", "#F9D838", "#B39416", "#FAE791", "#D3BE6F", "#AB954B", 
                "#756326", "#EEE7C7", "#C6BFA2", "#787259"],
            6: ["#A8BC16", "#B6C931", "#758616", "#D8DF93", "#ADB76D", "#85914B", 
                "#535E2B", "#E6E9C7", "#BCC2A3", "#6E745D"],
            7: ["#05A25D", "#41B97B", "#057447", "#9CDAAD", "#76B28B", "#4F8969", 
                "#245640", "#C3E0CC", "#9DB7A6", "#53695D"],
            8: ["#058781", "#05ABA0", "#056966", "#7ECDC2", "#55A49C", "#2B7E78", 
                "#054B4B", "#BEE0DA", "#98B7B2", "#4E6B66"],
            9: ["#05729C", "#0599BA", "#055878", "#79BBCA", "#5193A5", "#246D7F", 
                "#05495B", "#C6DDE2", "#9EB5BA", "#4F676F"],
            10: ["#055EA6", "#2B83C1", "#054782", "#83A8C9", "#5D80A1", "#365B7F", 
                 "#193B56", "#C1CDD5", "#9BA6B0", "#4C5967"],
            11: ["#534DA1", "#7577BD", "#3E387E", "#A2A0C7", "#787AA1", "#55567E", 
                 "#333555", "#C9CAD5", "#A2A3B0", "#565869"],
            12: ["#813D8B", "#A167A9", "#602B6C", "#B89BB9", "#907395", "#6C4D73", 
                 "#432E4B", "#CFC9D1", "#ABA1AC", "#605665"],
            13: ["#AD356F", "#CF6B8F", "#862658", "#D9A1B4", "#B47A8C", "#8B5367", 
                 "#60354B", "#E4D5DA", "#BCADB1", "#725E66"]
        }
        
        # 构建颜色到位置的映射
        self.color_to_position = {}
        for category, colors in self.color_palette.items():
            for index, color in enumerate(colors):
                self.color_to_position[color.upper()] = {
                    "category": category,
                    "index": index
                }
    
    def get_color_position(self, hex_color):
        """
        获取颜色在调色板中的位置
        返回: {"category": 分类号, "index": 索引}
        """
        hex_color = hex_color.upper()
        if hex_color in self.color_to_position:
            return self.color_to_position[hex_color]
        
        # 如果找不到完全匹配，使用最相似颜色
        return self.find_closest_color(hex_color)
    
    def find_closest_color(self, hex_color):
        """
        找到最接近的颜色（基于RGB欧几里得距离）
        """
        target_rgb = self.hex_to_rgb(hex_color)
        min_distance = float('inf')
        closest_position = None
        
        for color, position in self.color_to_position.items():
            color_rgb = self.hex_to_rgb(color)
            distance = sum((a - b) ** 2 for a, b in zip(target_rgb, color_rgb)) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                closest_position = position
        
        return closest_position
    
    @staticmethod
    def hex_to_rgb(hex_color):
        """将十六进制颜色转换为RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def get_category_color_count(self, category):
        """获取某个分类的颜色数量"""
        return len(self.color_palette.get(category, []))
