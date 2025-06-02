import pygame
import sys
import random
from pygame.locals import *

# 初始化pygame
pygame.init()

# 屏幕设置
WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("共享单车动态定价模拟")

# 莫兰迪色系颜色定义
BACKGROUND = (238, 232, 232)  # 淡粉色背景
PANEL_BG = (250, 248, 248)    # 白色面板
ACCENT = (176, 147, 147)      # 主色调粉色
ACCENT_LIGHT = (216, 201, 201) # 浅粉色
BUTTON_COLOR = (216, 201, 201) # 按钮颜色
BUTTON_HOVER = (176, 147, 147)  # 按钮悬停颜色
TEXT_COLOR = (70, 70, 70)     # 深灰色文本
SUCCESS = (127, 185, 127)      # 成功绿色
WARNING = (224, 167, 124)      # 警告橙色
# 调整区域颜色
AREA_COLORS = [(206, 178, 164), (172, 186, 196), (196, 172, 186)]  # 区域颜色

# 字体 - 使用多种字体区分层级
try:
    # 标题使用黑体
    font_large = pygame.font.SysFont("SimHei", 36, bold=True)
    # 副标题使用楷体
    font_subtitle = pygame.font.SysFont("KaiTi", 24)
    # 正文使用宋体
    font_medium = pygame.font.SysFont("SimSun", 18)  # 减小字号
    font_small = pygame.font.SysFont("SimSun", 14)   # 减小字号
    font_tiny = pygame.font.SysFont("SimSun", 12)    # 减小字号
except:
    # 如果字体不可用，使用默认字体
    font_large = pygame.font.SysFont(None, 40, bold=True)
    font_subtitle = pygame.font.SysFont(None, 24)
    font_medium = pygame.font.SysFont(None, 18)
    font_small = pygame.font.SysFont(None, 14)
    font_tiny = pygame.font.SysFont(None, 12)

# 自行车图标（简化的SVG）
BIKE_ICON = [
    "    o    ",
    "   /|\\   ",
    "  / | \\  ",
    "  | | |  ",
    "  | o |  ",
    "  |/|\\|  ",
    "__|_|_|__"
]

# 游戏状态
class GameState:
    def __init__(self):
        self.current_time = 0  # 0=早高峰, 1=日间, 2=晚高峰, 3=夜间
        self.time_names = ["早高峰 (7:00-9:00)", "日间 (10:00-16:00)", "晚高峰 (17:00-19:00)", "夜间 (20:00-22:00)"]
        self.day = 1
        self.total_revenue = 0
        self.total_cost = 0
        self.total_penalty = 0
        self.game_phase = "cover"  # cover, playing, day_summary
        self.day_history = []
        
        # 区域数据
        self.areas = {
            "商业区": {"demand": 4.5, "bikes": 35, "price": 2.5, "optimal": 30},
            "住宅区": {"demand": 3.0, "bikes": 20, "price": 1.8, "optimal": 25},
            "大学区": {"demand": 4.0, "bikes": 25, "price": 2.0, "optimal": 35}
        }
        
        self.strategies = {
            "高峰溢价": False,
            "需求激励": False,
            "夜间折扣": False
        }
        
        self.weather = "sunny"  # sunny, rain, heat
        self.last_results = (0, 0, 0, 0)  # 存储上一步结果
        
    def calculate_demand(self, area):
        """计算当前时段的需求"""
        base = self.areas[area]["demand"]
        price = self.areas[area]["price"]
        time_factor = [1.8, 1.0, 1.5, 0.7][self.current_time]
        
        # 价格弹性
        elasticity = -0.3 if self.current_time in [0, 2] else -0.4
        price_effect = 1 + elasticity * (price - 2.0) / 0.5
        
        # 天气影响
        weather_factor = 1.0
        if self.weather == "rain":
            weather_factor = 0.6
        elif self.weather == "heat":
            weather_factor = 1.3 if self.current_time == 3 else 1.1
        
        # 策略影响
        strategy_factor = 1.0
        if self.strategies["高峰溢价"] and self.current_time in [0, 2]:
            strategy_factor = 1.3
        elif self.strategies["夜间折扣"] and self.current_time == 3:
            strategy_factor = 0.8
        
        demand = base * time_factor * price_effect * weather_factor * strategy_factor
        return max(0.5, min(5.0, demand))
    
    def calculate_revenue(self):
        """计算收入"""
        revenue = 0
        for area in self.areas:
            demand = self.calculate_demand(area)
            usage = min(demand * 8, self.areas[area]["bikes"])
            revenue += usage * self.areas[area]["price"]
        return revenue
    
    def calculate_costs(self):
        """计算成本"""
        # 调度成本
        relocation_cost = 0
        for area in self.areas:
            imbalance = abs(self.areas[area]["bikes"] - self.areas[area]["optimal"])
            relocation_cost += imbalance * 0.8
        
        # 维护成本
        maintenance = sum([data["bikes"] * 0.2 for data in self.areas.values()])
        
        # 策略成本
        strategy_cost = 0
        if self.strategies["高峰溢价"]:
            strategy_cost += 100
        if self.strategies["需求激励"]:
            strategy_cost += 70
        if self.strategies["夜间折扣"]:
            strategy_cost += 50
        
        return relocation_cost + maintenance + strategy_cost
    
    def calculate_penalty(self):
        """计算罚款"""
        penalty = 0
        # 车辆分布不均衡罚款
        for area in self.areas:
            imbalance = abs(self.areas[area]["bikes"] - self.areas[area]["optimal"])
            if imbalance > 15:
                penalty += imbalance * 0.5
        
        # 需求未满足罚款
        for area in self.areas:
            demand = self.calculate_demand(area)
            if self.areas[area]["bikes"] < demand * 0.7:
                penalty += (demand * 0.7 - self.areas[area]["bikes"]) * 1.0
        
        return penalty
    
    def advance_time(self):
        """推进到下一个时段"""
        # 保存当前时段结果
        revenue = self.calculate_revenue()
        cost = self.calculate_costs()
        penalty = self.calculate_penalty()
        net = revenue - cost - penalty
        
        self.total_revenue += revenue
        self.total_cost += cost
        self.total_penalty += penalty
        
        # 更新到下一个时段
        self.current_time = (self.current_time + 1) % 4
        
        # 如果一天结束
        if self.current_time == 0:
            # 保存当天结果
            day_result = {
                "day": self.day,
                "revenue": self.total_revenue - sum(d.get('revenue', 0) for d in self.day_history),
                "cost": self.total_cost - sum(d.get('cost', 0) for d in self.day_history),
                "penalty": self.total_penalty - sum(d.get('penalty', 0) for d in self.day_history),
                "net": net,
                "weather": self.weather
            }
            self.day_history.append(day_result)
            
            self.day += 1
            # 每天开始时随机天气
            self.weather = random.choices(["sunny", "rain", "heat"], weights=[0.7, 0.2, 0.1])[0]
            
            # 重置策略
            for key in self.strategies:
                self.strategies[key] = False
            
            # 动态调整理想单车数量
            for area in self.areas:
                self.areas[area]["optimal"] = max(20, min(50, self.areas[area]["optimal"] + random.randint(-3, 3)))
            
            # 进入每日总结
            self.game_phase = "day_summary"
        
        self.last_results = (revenue, cost, penalty, net)
        return revenue, cost, penalty, net

# 按钮类
class Button:
    def __init__(self, x, y, width, height, text, color=BUTTON_COLOR, hover_color=BUTTON_HOVER):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        self.hover_color = hover_color
        self.text = text
        self.is_hovered = False
        
    def draw(self, surface):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (220, 220, 220), self.rect, 1, border_radius=8)
        
        text_surf = font_medium.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
        
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        
    def is_clicked(self, pos, event):
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(pos)
        return False

# 滑块类
class Slider:
    def __init__(self, x, y, width, min_val, max_val, initial_val, label):
        self.rect = pygame.Rect(x, y, width, 8)
        self.knob_rect = pygame.Rect(x + (initial_val - min_val) / (max_val - min_val) * width - 10, y - 6, 20, 20)
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial_val
        self.label = label
        self.dragging = False
        
    def draw(self, surface):
        # 绘制滑轨
        pygame.draw.rect(surface, (200, 200, 200), self.rect, border_radius=4)
        
        # 绘制填充部分
        fill_width = (self.value - self.min_val) / (self.max_val - self.min_val) * self.rect.width
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
        pygame.draw.rect(surface, ACCENT, fill_rect, border_radius=4)
        
        # 绘制旋钮
        pygame.draw.circle(surface, ACCENT, self.knob_rect.center, 10)
        pygame.draw.circle(surface, (50, 50, 50), self.knob_rect.center, 10, 1)
        
        # 绘制标签和值
        label_surf = font_small.render(f"{self.label}: ¥{self.value:.1f}", True, TEXT_COLOR)
        surface.blit(label_surf, (self.rect.x, self.rect.y - 20))  # 缩小行间距

    def update(self, pos, events):
        for event in events:
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                if self.knob_rect.collidepoint(pos):
                    self.dragging = True
            elif event.type == MOUSEBUTTONUP and event.button == 1:
                self.dragging = False
        
        if self.dragging:
            # 更新旋钮位置
            self.knob_rect.centerx = max(self.rect.left, min(pos[0], self.rect.right))
            
            # 计算新值
            ratio = (self.knob_rect.centerx - self.rect.left) / self.rect.width
            self.value = self.min_val + ratio * (self.max_val - self.min_val)
            self.value = round(self.value * 2) / 2  # 四舍五入到0.5
            
        return self.value

# 策略复选框类
class Checkbox:
    def __init__(self, x, y, text, checked=False):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.checked = checked
        self.text = text
        self.is_hovered = False
        
    def draw(self, surface):
        # 绘制复选框
        color = ACCENT_LIGHT if self.is_hovered else (200, 200, 200)
        pygame.draw.rect(surface, color, self.rect, border_radius=4)
        pygame.draw.rect(surface, (100, 100, 100), self.rect, 1, border_radius=4)
        
        if self.checked:
            # 绘制勾选标记
            pygame.draw.line(surface, ACCENT, (self.rect.x+4, self.rect.y+10), 
                            (self.rect.x+8, self.rect.y+15), 2)
            pygame.draw.line(surface, ACCENT, (self.rect.x+8, self.rect.y+15), 
                            (self.rect.x+16, self.rect.y+5), 2)
        
        # 绘制文本
        text_surf = font_small.render(self.text, True, TEXT_COLOR)
        surface.blit(text_surf, (self.rect.x + 30, self.rect.y))
        
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        
    def toggle(self, pos, event):
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(pos):
                self.checked = not self.checked
                return True
        return False

# 绘制自行车图标
def draw_bike(surface, x, y, size=1.0, color=ACCENT):
    for i, line in enumerate(BIKE_ICON):
        for j, char in enumerate(line):
            if char != ' ':
                pygame.draw.circle(surface, color, (x + j*int(size*4), y + i*int(size*4)), int(size*2))

# 创建游戏状态
game = GameState()

# 封面按钮
start_btn = Button(WIDTH//2 - 100, HEIGHT//2 + 150, 200, 50, "开始游戏")

# 游戏内按钮
# 调整按钮位置向左移动
execute_btn = Button(560, HEIGHT - 100, 180, 45, "执行决策")  # 向左移动50像素
next_btn = Button(780, HEIGHT - 100, 180, 45, "下一时段")    # 向左移动50像素
continue_btn = Button(WIDTH//2 - 100, HEIGHT - 170, 200, 45, "继续")
back_btn = Button(WIDTH//2 - 100, HEIGHT -110, 200, 45, "返回封面")

# 滑块
sliders = [
    Slider(580, 150, 300, 1.0, 4.0, 2.5, "商业区价格"),
    Slider(580, 200, 300, 0.5, 3.0, 1.8, "住宅区价格"),
    Slider(580, 250, 300, 1.0, 3.5, 2.0, "大学区价格")
]

# 策略复选框
# 向下调整复选框位置
checkboxes = [
    Checkbox(580, 332, "高峰时段溢价 (+30%)"),
    Checkbox(580, 358, "晚高峰需求激励 (+20%需求)"),
    Checkbox(580, 383, "夜间折扣 (-20%价格)")
]

# 主游戏循环
clock = pygame.time.Clock()
running = True

while running:
    mouse_pos = pygame.mouse.get_pos()
    events = pygame.event.get()
    
    for event in events:
        if event.type == QUIT:
            running = False
        
        # 处理封面按钮
        if game.game_phase == "cover":
            if start_btn.is_clicked(mouse_pos, event):
                game.game_phase = "playing"
        
        # 处理游戏内按钮
        elif game.game_phase == "playing":
            if execute_btn.is_clicked(mouse_pos, event):
                # 更新区域价格
                game.areas["商业区"]["price"] = sliders[0].value
                game.areas["住宅区"]["price"] = sliders[1].value
                game.areas["大学区"]["price"] = sliders[2].value
                
                # 更新策略
                game.strategies["高峰溢价"] = checkboxes[0].checked
                game.strategies["需求激励"] = checkboxes[1].checked
                game.strategies["夜间折扣"] = checkboxes[2].checked
                
                # 计算并显示结果
                game.last_results = (game.calculate_revenue(), game.calculate_costs(), 
                                   game.calculate_penalty(), 
                                   game.calculate_revenue() - game.calculate_costs() - game.calculate_penalty())
            
            if next_btn.is_clicked(mouse_pos, event):
                # 推进到下一个时段
                game.advance_time()
                
                # 更新滑块值
                sliders[0].value = game.areas["商业区"]["price"]
                sliders[1].value = game.areas["住宅区"]["price"]
                sliders[2].value = game.areas["大学区"]["price"]
                
                # 重置复选框
                for cb in checkboxes:
                    cb.checked = False
            
            # 处理复选框点击
            for cb in checkboxes:
                cb.toggle(mouse_pos, event)
        
        # 处理总结页面按钮
        elif game.game_phase == "day_summary":
            if continue_btn.is_clicked(mouse_pos, event):
                game.game_phase = "playing"
            if back_btn.is_clicked(mouse_pos, event):
                game.game_phase = "cover"
    
    # 更新滑块值
    if game.game_phase == "playing":
        for slider in sliders:
            slider.update(mouse_pos, events)
    
    # 更新悬停状态
    if game.game_phase == "cover":
        start_btn.check_hover(mouse_pos)
    elif game.game_phase == "playing":
        execute_btn.check_hover(mouse_pos)
        next_btn.check_hover(mouse_pos)
        for cb in checkboxes:
            cb.check_hover(mouse_pos)
    elif game.game_phase == "day_summary":
        continue_btn.check_hover(mouse_pos)
        back_btn.check_hover(mouse_pos)
    
    # 绘制界面
    screen.fill(BACKGROUND)
    
    # 封面页面
    if game.game_phase == "cover":
        # 绘制标题
        title = font_large.render("共享单车动态定价模拟", True, ACCENT)
        subtitle = font_subtitle.render("经济学实验游戏", True, TEXT_COLOR)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//3 - 50))
        screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, HEIGHT//3 + 20))
        
        # 绘制游戏简介
        desc = [
            "游戏简介:",
            "作为共享单车区域运营经理，你需要制定动态定价策略",
            "根据时段、区域和天气调整价格，最大化收益",
            "体验经济学中的需求弹性、价格歧视和成本管理"
        ]
        
        for i, line in enumerate(desc):
            text = font_medium.render(line, True, TEXT_COLOR)
            screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - 20 + i*30))
        
        # 绘制按钮
        start_btn.draw(screen)
        
        # 操作提示
        help_text = font_tiny.render("点击'开始游戏'按钮开始", True, (150, 150, 150))
        screen.blit(help_text, (WIDTH//2 - help_text.get_width()//2, HEIGHT - 70))
    
    # 游戏主页面
    elif game.game_phase == "playing":
        # 绘制标题栏
        pygame.draw.rect(screen, ACCENT, (0, 0, WIDTH, 70))
        title = font_large.render(f"第 {game.day} 天: {game.time_names[game.current_time]}", True, (255, 255, 255))
        screen.blit(title, (20, 20))
        
        # 天气显示（使用文字代替图标）
        weather_text = font_subtitle.render(f"天气: {'晴天' if game.weather=='sunny' else '雨天' if game.weather=='rain' else '高温'}", True, (255, 255, 255))
        screen.blit(weather_text, (WIDTH - 160, 22))
        
        # 绘制区域信息面板
        pygame.draw.rect(screen, PANEL_BG, (40, 90, 500, 550), border_radius=8)
        area_title = font_medium.render("区域信息", True, ACCENT)
        screen.blit(area_title, (60, 110))
        
        # 绘制区域信息
        area_height = 140
        area_margin = 20
        
        for i, (area, data) in enumerate(game.areas.items()):
            y = 150 + i * (area_height + area_margin)
            
            # 绘制区域卡片
            pygame.draw.rect(screen, AREA_COLORS[i], (60, y, 460, area_height), border_radius=8)
            
            # 区域标题
            area_title = font_medium.render(area, True, (255, 255, 255))
            screen.blit(area_title, (78, y + 15))
            
            # 需求显示
            demand = game.calculate_demand(area)
            demand_text = font_small.render(f"需求: {'★' * int(demand)}{'☆' * (5 - int(demand))} ({demand:.1f}/5.0)", True, (255, 255, 255))
            screen.blit(demand_text, (78, y + 45))
            
            # 单车数量
            bikes_text = font_small.render(f"可用单车: {data['bikes']} 辆", True, (255, 255, 255))
            screen.blit(bikes_text, (78, y + 70))
            
            # 理想单车数量
            optimal_text = font_small.render(f"理想数量: {data['optimal']} 辆", True, (255, 255, 255))
            screen.blit(optimal_text, (78, y + 95))
        
        # 绘制价格调整面板
        pygame.draw.rect(screen, PANEL_BG, (560, 90, 400, 180), border_radius=8)
        price_title = font_medium.render("价格调整", True, ACCENT)
        screen.blit(price_title, (580, 105))
        
        # 绘制滑块
        for slider in sliders:
            slider.draw(screen)
        
        # 绘制策略面板（增加高度）
        pygame.draw.rect(screen, PANEL_BG, (560, 290, 400, 120), border_radius=8)  # 增加高度20像素
        strategy_title = font_medium.render("时段策略", True, ACCENT)
        screen.blit(strategy_title, (580, 300))
        
        # 绘制复选框
        for cb in checkboxes:
            cb.draw(screen)
        
        # 绘制结果面板（下移20像素）
        pygame.draw.rect(screen, PANEL_BG, (560, 430, 400, 150), border_radius=8)  # 下移20像素
        result_title = font_medium.render("运营结果", True, ACCENT)
        screen.blit(result_title, (580, 440))
        
        # 绘制当前时段结果
        revenue, cost, penalty, net = game.last_results
        result_texts = [
            f"时段收入: ¥{revenue:.1f}",
            f"运营成本: ¥{cost:.1f}",
            f"罚款损失: ¥{penalty:.1f}",
            f"时段净收益: ¥{net:.1f}"
        ]
        
        for i, text in enumerate(result_texts):
            color = TEXT_COLOR
            if i == 3:
                color = SUCCESS if net >= 0 else WARNING
            text_surf = font_small.render(text, True, color)
            screen.blit(text_surf, (580, 465 + i*25))
        
        # 绘制按钮（已向左调整位置）
        execute_btn.draw(screen)
        next_btn.draw(screen)
        
        # 操作提示
        help_text = font_tiny.render("操作流程: 1. 调整价格滑块 2. 选择时段策略 3. 点击'执行决策' 4. 点击'下一时段'", True, (150, 150, 150))
        text_width = help_text.get_width()
        x = (WIDTH - text_width) // 2
        screen.blit(help_text, (x, HEIGHT - 40))

    # 每日总结页面
    elif game.game_phase == "day_summary":
        # 绘制标题
        title = font_large.render(f"第 {game.day - 1} 天运营总结", True, ACCENT)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))

        # 绘制总结卡片
        pygame.draw.rect(screen, PANEL_BG, (WIDTH // 2 - 350, 100, 700, 400), border_radius=10)

        # 获取最后一天的结果
        if game.day_history:
            day_result = game.day_history[-1]

            # 绘制结果数据
            result_texts = [
                f"日收入: ¥{day_result['revenue']:.1f}",
                f"日成本: ¥{day_result['cost']:.1f}",
                f"日罚款: ¥{day_result['penalty']:.1f}",
                f"日净收益: ¥{day_result['net']:.1f}",
                f"天气: {'晴天' if day_result['weather'] == 'sunny' else '雨天' if day_result['weather'] == 'rain' else '高温'}"
                # 修改为文字
            ]

            for i, text in enumerate(result_texts):
                color = TEXT_COLOR
                if i == 3:
                    color = SUCCESS if day_result['net'] >= 0 else WARNING
                text_surf = font_medium.render(text, True, color)
                screen.blit(text_surf, (WIDTH // 2 - text_surf.get_width() // 2, 150 + i * 50))

            # 根据不同的游戏结果生成不同的经济学分析文本
            net_income = day_result['net']
            penalty = day_result['penalty']
            cost = day_result['cost']

            if net_income > 0:
                if penalty == 0:
                    analysis_texts = [
                        "当日净收益为正且无罚款，说明你对车辆资源的分配十分合理，有效避免了因车辆分布不均衡和需求未满足带来的罚款损失。",
                        "同时，你可能很好地利用了价格弹性理论，在需求对价格变化不敏感的时段提高了价格，从而增加了收益。"
                    ]
                else:
                    analysis_texts = [
                        "尽管当日有罚款，但净收益仍为正，说明你的定价策略在一定程度上弥补了罚款带来的损失。",
                        "不过，仍需注意合理分配车辆资源，以降低调度成本和罚款损失。"
                    ]
            else:
                if penalty > 0:
                    analysis_texts = [
                        "当日净收益为负且有罚款，表明车辆资源分配不合理，导致了较高的调度成本和罚款损失。",
                        "你需要重新评估各区域的需求，调整车辆分布，避免因车辆不足或过剩而产生罚款。"
                    ]
                else:
                    analysis_texts = [
                        "当日净收益为负但无罚款，可能是定价策略不当导致收入过低，或者运营成本过高。",
                        "你可以考虑在需求高峰时段适当提高价格，同时优化运营流程以降低成本。"
                    ]
        else:
            # 如果没有历史数据，显示默认分析文本
            analysis_texts = [
                "目前暂无运营数据可供分析。",
                "请继续运营，后续将根据您的运营情况给出详细的经济学分析。"
            ]

        # 绘制经济学分析
        pygame.draw.rect(screen, (240, 248, 255), (WIDTH // 2 - 350, 380, 700, 120), border_radius=8)
        analysis_title = font_small.render("经济学分析:", True, ACCENT)
        screen.blit(analysis_title, (WIDTH // 2 - 330, 390))

        for i, text in enumerate(analysis_texts):
            analysis_text = font_tiny.render(text, True, TEXT_COLOR)
            screen.blit(analysis_text, (WIDTH // 2 - 330, 420 + i * 20))

        # 绘制按钮
        continue_btn.draw(screen)
        back_btn.draw(screen)

        # 操作提示
        help_text = font_tiny.render("点击'继续'进入下一天，或点击'返回封面'重新开始", True, (150, 150, 150))
        screen.blit(help_text, (WIDTH // 2 - help_text.get_width() // 2, HEIGHT - 40))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()