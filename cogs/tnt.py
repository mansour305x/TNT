import discord
from discord.ext import commands
from discord import ui

class TNTMessage(ui.View):
    """View for TNT main button"""
    
    def __init__(self):
        super().__init__()
        self.add_item(ui.Button(
            label="Close",
            style=discord.ButtonStyle.secondary,
            emoji="✖️"
        ))
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: ui.Item):
        await interaction.response.send_message("An error occurred!", ephemeral=True)


class TNT(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="tnt",
        description="Main TNT bot menu"
    )
    async def tnt_command(self, interaction: discord.Interaction):
        """Display the main TNT menu with a greeting message"""
        
        embed = discord.Embed(
            title="🧨 TNT - Main Menu",
            description=(
                "**Message to my friends:**\n\n"
                "I wanted to dedicate this bot to your alliance and I hope it will be a gift "
                "that brings you satisfaction and joy.\n\n"
                "**Your friend ღღ The Danger**"
            ),
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="About",
            value="This bot provides various utilities for alliance management and coordination.",
            inline=False
        )
        
        embed.set_footer(text="TNT Bot - Dedicated to the Alliance")
        
        view = TNTMessage()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)


async def setup(bot):
    await bot.add_cog(TNT(bot))
